from __future__ import annotations

import httpx
import numpy as np
from helpers import assert_deterministic, assert_fast_and_small, assert_solvable, client_for

from tensorgoat.core.scenario import load_service_params
from tensorgoat.scenarios.s06_ghost_badge.model import hamming, probe_inversion

SID = "s06_ghost_badge"
CELLS = 64
GRAY = [0.5] * CELLS


def _params(generated) -> dict:
    _, state, _ = generated(SID)
    return load_service_params(state.internal_dir(SID))


def _vault_pattern(generated) -> list[int]:
    return [int(cell) for cell in _params(generated)["vault_pattern"]]


def _my_badge(generated) -> list[int]:
    _, _, ctx = generated(SID)
    text = (ctx.workspace / "my_badge.txt").read_text(encoding="utf-8")
    return [int(char == "#") for line in text.splitlines() for char in line]


def _with_wrong_cells(pattern: list[int], count: int) -> list[int]:
    changed = list(pattern)
    for index in range(count):
        changed[index * 7] = 1 - changed[index * 7]
    return changed


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    def well_within_budget(url: str) -> None:
        info = httpx.get(url + "/").json()
        assert info["query_budget"] - info["queries_remaining"] <= 300

    assert_solvable(SID, isolated_home, after_solve=well_within_budget)


def test_workspace_files(generated):
    _, _, ctx = generated(SID)
    params = _params(generated)
    assert sorted(path.name for path in ctx.workspace.iterdir()) == [
        "my_badge.txt",
        "reader_notes.md",
    ]
    lines = (ctx.workspace / "my_badge.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8 and all(len(line) == 8 and set(line) <= {"#", "."} for line in lines)
    notes = (ctx.workspace / "reader_notes.md").read_text(encoding="utf-8")
    assert "{{" not in notes and params["your_badge"] in notes
    assert params["your_badge"] != params["vault_keyholder"]
    # The keyholder's pattern is nowhere in the workspace, in any rendering.
    vault = _vault_pattern(generated)
    rendered = "".join("#" if cell else "." for cell in vault)
    for path in ctx.workspace.iterdir():
        text = path.read_text(encoding="utf-8").replace("\n", "")
        assert rendered not in text and "".join(map(str, vault)) not in text


def test_service_contract(generated):
    client = client_for(generated, SID)
    params = _params(generated)
    info = client.get("/").json()
    assert info["scenario"] == SID and info["message"]
    assert info["grid"] == [8, 8] and info["cells"] == CELLS
    assert info["pixel_range"] == [0.0, 1.0]
    assert info["holders"] == [f"B-0{n}" for n in range(1, 9)]
    assert info["your_badge"] == params["your_badge"]
    assert info["vault_keyholder"] == params["vault_keyholder"]
    assert info["query_budget"] == info["queries_remaining"] == 600
    assert info["unlock_tolerance"] == 4 and info["unlock_attempts_per_minute"] == 10

    ok = client.post("/recognise", json={"pixels": GRAY})
    assert ok.status_code == 200
    answer = ok.json()
    assert set(answer) == {"best_match", "confidences", "queries_remaining"}
    assert list(answer["confidences"]) == info["holders"]
    assert abs(sum(answer["confidences"].values()) - 1.0) < 1e-3
    assert all(round(value, 4) == value for value in answer["confidences"].values())
    assert answer["best_match"] == max(answer["confidences"], key=answer["confidences"].get)
    assert answer["queries_remaining"] == 599

    for bad in ([0.5] * 63, [0.5] * 65, []):
        response = client.post("/recognise", json={"pixels": bad})
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_REQUEST"
    assert client.post("/recognise", json={}).json()["error_code"] == "INVALID_REQUEST"
    for bad in ([1.5] + [0.5] * 63, [-0.1] + [0.5] * 63):
        response = client.post("/recognise", json={"pixels": bad})
        assert response.status_code == 400
        assert response.json()["error_code"] == "OUT_OF_RANGE"
    assert client.get("/").json()["queries_remaining"] == 599, "invalid requests are free"

    for bad in ([0] * 63, [0] * 65, [2] + [0] * 63, [-1] + [0] * 63, [0.5] + [0] * 63):
        response = client.post("/unlock", json={"cells": bad})
        assert response.status_code == 422, bad[:1]
        assert response.json()["error_code"] == "INVALID_REQUEST"


def test_reader_recognises_real_badges(generated):
    client = client_for(generated, SID)
    params = _params(generated)
    mine = client.post("/recognise", json={"pixels": _my_badge(generated)}).json()
    assert mine["best_match"] == params["your_badge"]
    assert mine["confidences"][params["your_badge"]] > 0.9
    vault = client.post("/recognise", json={"pixels": _vault_pattern(generated)}).json()
    assert vault["best_match"] == params["vault_keyholder"]


def test_gray_scan_leaves_the_model_undecided(generated):
    """Tuned requirement: single cells must visibly move the keyholder's confidence."""
    client = client_for(generated, SID)
    keyholder = _params(generated)["vault_keyholder"]
    start = client.post("/recognise", json={"pixels": GRAY}).json()["confidences"][keyholder]
    assert 0.02 <= start <= 0.6
    moved = 0
    for cell in range(CELLS):
        scan = list(GRAY)
        scan[cell] = 1.0
        value = client.post("/recognise", json={"pixels": scan}).json()["confidences"][keyholder]
        moved += value != start
    assert moved >= 60, "nearly every cell must change the reported confidence"


def test_intended_attack_lands_inside_the_margin(generated):
    """Tuned requirement: the probe attack misses at most attack_margin (2) cells."""
    scenario, _, _ = generated(SID)
    params = _params(generated)
    assert scenario.tunable_params["attack_margin"] == 2
    keyholder = params["holder_ids"].index(params["vault_keyholder"])
    rebuilt = probe_inversion(params["coef"], params["intercept"], keyholder)
    assert hamming(rebuilt, params["vault_pattern"]) <= 2
    you = params["holder_ids"].index(params["your_badge"])
    practice = probe_inversion(params["coef"], params["intercept"], you)
    assert hamming(practice, _my_badge(generated)) <= 4, "practising on your own badge works"


def test_unlock_tolerance_boundary(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    _, _, ctx = generated(SID)
    vault = _vault_pattern(generated)
    exact = client.post("/unlock", json={"cells": vault})
    assert exact.status_code == 200 and exact.json()["flag"] == ctx.flag
    assert exact.json()["holder"] == _params(generated)["vault_keyholder"]
    assert client.post("/unlock", json={"cells": _with_wrong_cells(vault, 4)}).status_code == 200
    denied = client.post("/unlock", json={"cells": _with_wrong_cells(vault, 5)})
    assert denied.status_code == 400
    assert denied.json()["error_code"] == "ACCESS_DENIED" and "flag" not in denied.json()


def test_unintended_other_badges_and_trivial_patterns_do_not_open(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    vault = _vault_pattern(generated)
    mine = _my_badge(generated)
    assert hamming(mine, vault) > 16
    for pattern in (mine, [0] * CELLS, [1] * CELLS, [1 - cell for cell in vault]):
        response = client.post("/unlock", json={"cells": pattern})
        assert response.status_code == 400
        assert response.json()["error_code"] == "ACCESS_DENIED"


def test_unintended_random_guessing_never_works(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    rng = np.random.default_rng(0)
    for _ in range(300):
        guess = [int(cell) for cell in rng.integers(0, 2, size=CELLS)]
        response = client.post("/unlock", json={"cells": guess})
        assert response.status_code == 400
        assert "flag" not in response.json()


def test_unintended_unlock_leaks_no_distance(generated):
    """Open or denied only: /unlock must not help to home in on the pattern."""
    client = client_for(generated, SID, rate_limit_per_minute=0)
    vault = _vault_pattern(generated)
    bodies = set()
    for wrong in (5, 6, 9, 20, 40, 64):
        flipped = [1 - cell if index < wrong else cell for index, cell in enumerate(vault)]
        response = client.post("/unlock", json={"cells": flipped})
        assert response.status_code == 400
        assert set(response.json()) == {"error_code", "message"}
        bodies.add(response.text)
    assert len(bodies) == 1, "the answer must be identical however close the pattern is"


def test_unintended_rate_limit_blocks_unlock_brute_force(generated):
    client = client_for(generated, SID)  # default: 10 attempts per minute
    vault = _vault_pattern(generated)
    for _ in range(10):
        assert client.post("/unlock", json={"cells": [0] * CELLS}).status_code == 400
    for pattern in ([0] * CELLS, vault):
        limited = client.post("/unlock", json={"cells": pattern})
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "RATE_LIMITED"
        assert "flag" not in limited.json()
    # /recognise is governed by its own budget, not by the unlock limiter.
    assert client.post("/recognise", json={"pixels": GRAY}).status_code == 200


def test_unintended_budget_is_enforced(generated):
    client = client_for(generated, SID, query_budget=5)
    for _ in range(5):
        assert client.post("/recognise", json={"pixels": GRAY}).status_code == 200
    for _ in range(3):
        blocked = client.post("/recognise", json={"pixels": GRAY})
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "BUDGET_EXCEEDED"
        assert "confidences" not in blocked.json()
    assert client.get("/").json()["queries_remaining"] == 0
    # A restart (new app, new store) resets the budget.
    restarted = client_for(generated, SID)
    assert restarted.post("/recognise", json={"pixels": GRAY}).status_code == 200


def test_error_codes_do_not_depend_on_language(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    english = client.post("/unlock", json={"cells": [0] * CELLS})
    other = client.post("/unlock", json={"cells": [0] * CELLS}, headers={"Accept-Language": "xx"})
    assert english.json()["error_code"] == other.json()["error_code"] == "ACCESS_DENIED"
    assert other.json()["message"] == english.json()["message"], "unknown language -> English"


def test_resource_budget(tmp_path):
    assert_fast_and_small(SID, tmp_path / "home")
