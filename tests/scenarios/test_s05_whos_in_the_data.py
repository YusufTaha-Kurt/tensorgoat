from __future__ import annotations

import csv
import itertools

import numpy as np
from helpers import assert_deterministic, assert_fast_and_small, assert_solvable, client_for

from tensorgoat.core.scenario import load_service_params

SID = "s05_whos_in_the_data"
FEATURES = (
    "age",
    "visits_per_month",
    "avg_basket",
    "tenure_months",
    "support_tickets",
    "discount_usage",
)


def _candidates(generated) -> list[dict[str, str]]:
    _, _, ctx = generated(SID)
    with open(ctx.workspace / "candidates.csv", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _members(generated) -> set[str]:
    _, state, _ = generated(SID)
    return set(load_service_params(state.internal_dir(SID))["member_ids"])


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    assert_solvable(SID, isolated_home)


def test_candidates_file(generated):
    rows = _candidates(generated)
    assert len(rows) == 20
    assert list(rows[0]) == ["candidate_id", *FEATURES, "churned"]
    ids = [row["candidate_id"] for row in rows]
    assert len(set(ids)) == 20
    members = _members(generated)
    assert len(members) == 5 and members < set(ids)
    # Members must not be recognisable from their position or id order.
    assert [cid in members for cid in ids] != sorted((cid in members for cid in ids), reverse=True)
    assert "name" not in rows[0] and "email" not in rows[0], "no personal identifiers"


def test_confidence_gap_is_visible_to_a_beginner(generated):
    """Tuned requirement: members >= 0.95, at least 13 of 15 non-members <= 0.85."""
    client = client_for(generated, SID)
    members = _members(generated)
    member_conf, outsider_conf = [], []
    for row in _candidates(generated):
        features = [float(row[name]) for name in FEATURES]
        answer = client.post("/predict", json={"features": features}).json()
        assert answer["confidence"] == max(
            answer["churn_probability"], round(1 - answer["churn_probability"], 4)
        )
        if row["candidate_id"] in members:
            member_conf.append(answer["confidence"])
            # Members are predicted with their true label.
            assert (answer["churn_probability"] > 0.5) == (row["churned"] == "1")
        else:
            outsider_conf.append(answer["confidence"])
    assert min(member_conf) >= 0.95
    assert sum(conf <= 0.85 for conf in outsider_conf) >= 13
    assert max(outsider_conf) <= 0.90 < min(member_conf)


def test_service_contract(generated):
    client = client_for(generated, SID)
    info = client.get("/").json()
    assert info["scenario"] == SID
    assert info["features"] == list(FEATURES) and info["members_to_find"] == 5

    for bad in ([1.0] * 5, [1.0] * 7, []):
        response = client.post("/predict", json={"features": bad})
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_FEATURES"
    assert client.post("/predict", json={}).json()["error_code"] == "INVALID_REQUEST"

    ids = [row["candidate_id"] for row in _candidates(generated)]
    for bad in (ids[:4], ids[:6], [ids[0]] * 5, []):
        response = client.post("/submit_members", json={"candidate_ids": bad})
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_REQUEST"

    members = sorted(_members(generated))
    _, _, ctx = generated(SID)
    right = client.post("/submit_members", json={"candidate_ids": members})
    assert right.status_code == 200 and right.json()["flag"] == ctx.flag
    shuffled = client.post("/submit_members", json={"candidate_ids": members[::-1]})
    assert shuffled.status_code == 200, "order must not matter"


def test_unintended_random_guessing_rarely_works(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    ids = [row["candidate_id"] for row in _candidates(generated)]
    members = _members(generated)
    rng = np.random.default_rng(0)
    hits = 0
    for _ in range(100):
        guess = [str(cid) for cid in rng.choice(ids, size=5, replace=False)]
        response = client.post("/submit_members", json={"candidate_ids": guess})
        if response.status_code == 200:
            assert set(guess) == members
            hits += 1
        else:
            assert response.json()["error_code"] == "INCORRECT"
    assert hits <= 1, "1 in 15504 per guess: random guessing must (almost) never work"


def test_unintended_no_partial_credit_is_leaked(generated):
    client = client_for(generated, SID, rate_limit_per_minute=0)
    ids = [row["candidate_id"] for row in _candidates(generated)]
    members = sorted(_members(generated))
    outsiders = [cid for cid in ids if cid not in members]
    bodies = set()
    for right in range(5):  # 0..4 correct ids
        guess = members[:right] + outsiders[: 5 - right]
        response = client.post("/submit_members", json={"candidate_ids": guess})
        assert response.status_code == 400
        assert set(response.json()) == {"error_code", "message"}
        bodies.add(response.text)
    assert len(bodies) == 1, "the response must be identical however many ids are right"
    # Leave-one-out probing also learns nothing.
    for dropped, added in itertools.product(members, outsiders[:3]):
        guess = [cid for cid in members if cid != dropped] + [added]
        assert client.post("/submit_members", json={"candidate_ids": guess}).text in bodies


def test_unintended_rate_limit_blocks_brute_force(generated):
    client = client_for(generated, SID)  # default: 10 attempts per minute
    ids = [row["candidate_id"] for row in _candidates(generated)]
    members = sorted(_members(generated))
    outsiders = [cid for cid in ids if cid not in members]
    for _ in range(10):
        wrong = client.post("/submit_members", json={"candidate_ids": outsiders[:5]})
        assert wrong.status_code == 400
    for guess in (outsiders[:5], members):
        limited = client.post("/submit_members", json={"candidate_ids": guess})
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "RATE_LIMITED"
        assert "flag" not in limited.json()
    # /predict is not rate limited: the intended attack needs only 20 calls.
    features = [float(_candidates(generated)[0][name]) for name in FEATURES]
    assert client.post("/predict", json={"features": features}).status_code == 200


def test_resource_budget(tmp_path):
    assert_fast_and_small(SID, tmp_path / "home")
