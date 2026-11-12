from __future__ import annotations

import httpx
import numpy as np
from helpers import assert_deterministic, assert_fast_and_small, assert_solvable, client_for

from tensorgoat.core.scenario import load_service_params

SID = "s03_model_heist"


def _truth(generated) -> tuple[list[float], float]:
    _, state, _ = generated(SID)
    params = load_service_params(state.internal_dir(SID))
    return list(params["weights"]), float(params["bias"])


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    def within_ten_queries(url: str) -> None:
        info = httpx.get(url + "/").json()
        assert info["query_budget"] - info["queries_remaining"] <= 10

    assert_solvable(SID, isolated_home, after_solve=within_ten_queries)


def test_service_contract(generated):
    client = client_for(generated, SID)
    info = client.get("/").json()
    assert info["scenario"] == SID
    assert len(info["features"]) == 5 and info["feature_range"] == [0.0, 1.0]
    assert info["query_budget"] == 50 and info["queries_remaining"] == 50
    assert info["message"]

    ok = client.post("/score", json={"features": [0.1, 0.2, 0.3, 0.4, 0.5]})
    assert ok.status_code == 200
    probability = ok.json()["approval_probability"]
    assert 0 < probability < 1 and round(probability, 6) == probability
    assert ok.json()["queries_remaining"] == 49

    for bad in ([0.1] * 4, [0.1] * 6, [0.1, 0.2, 0.3, 0.4, 1.5], [-0.1, 0, 0, 0, 0]):
        response = client.post("/score", json={"features": bad})
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_FEATURES"
    malformed = client.post("/score", json={"feature": "nope"})
    assert malformed.status_code == 422
    assert malformed.json()["error_code"] == "INVALID_REQUEST"
    assert client.get("/").json()["queries_remaining"] == 49, "invalid requests are free"

    wrong_length = client.post("/verify", json={"weights": [0.0], "bias": 0.0})
    assert wrong_length.json()["error_code"] == "INVALID_REQUEST"


def test_probabilities_do_not_saturate_on_simple_probes(generated):
    client = client_for(generated, SID)
    probes = [[0.0] * 5] + [[float(i == j) for j in range(5)] for i in range(5)]
    for features in probes:
        probability = client.post("/score", json={"features": features}).json()[
            "approval_probability"
        ]
        assert 0.01 <= probability <= 0.99


def test_verify_accepts_within_tolerance_only(generated):
    client = client_for(generated, SID)
    weights, bias = _truth(generated)
    exact = client.post("/verify", json={"weights": weights, "bias": bias})
    assert exact.status_code == 200
    _, state, ctx = generated(SID)
    assert exact.json()["flag"] == ctx.flag

    close = [w + 0.04 for w in weights]
    assert client.post("/verify", json={"weights": close, "bias": bias - 0.04}).status_code == 200

    for index in range(5):
        off = list(weights)
        off[index] += 0.06
        response = client.post("/verify", json={"weights": off, "bias": bias})
        assert response.status_code == 400
        assert response.json() == {
            "error_code": "INCORRECT",
            "message": response.json()["message"],
        }, "no hint about which value is wrong"
    assert client.post("/verify", json={"weights": weights, "bias": bias + 0.06}).status_code == 400


def test_unintended_random_weights_do_not_verify(generated):
    client = client_for(generated, SID)
    rng = np.random.default_rng(0)
    for _ in range(300):
        guess = rng.uniform(-2, 2, size=6)
        response = client.post("/verify", json={"weights": list(guess[:5]), "bias": guess[5]})
        assert response.status_code == 400
        assert response.json()["error_code"] == "INCORRECT"
        assert "flag" not in response.json()
    zeros = client.post("/verify", json={"weights": [0.0] * 5, "bias": 0.0})
    assert zeros.json()["error_code"] == "INCORRECT"


def test_unintended_budget_is_enforced(generated):
    client = client_for(generated, SID)
    for _ in range(50):
        assert client.post("/score", json={"features": [0.5] * 5}).status_code == 200
    for _ in range(3):
        blocked = client.post("/score", json={"features": [0.5] * 5})
        assert blocked.status_code == 429
        assert blocked.json()["error_code"] == "BUDGET_EXCEEDED"
        assert "approval_probability" not in blocked.json()
    assert client.get("/").json()["queries_remaining"] == 0
    # A restart (new app, new store) resets the budget.
    restarted = client_for(generated, SID)
    assert restarted.post("/score", json={"features": [0.5] * 5}).status_code == 200


def test_error_codes_do_not_depend_on_language(generated):
    client = client_for(generated, SID)
    english = client.post("/verify", json={"weights": [0.0] * 5, "bias": 0.0})
    other = client.post(
        "/verify", json={"weights": [0.0] * 5, "bias": 0.0}, headers={"Accept-Language": "xx"}
    )
    assert english.json()["error_code"] == other.json()["error_code"] == "INCORRECT"
    assert other.json()["message"] == english.json()["message"], "unknown language -> English"


def test_resource_budget(tmp_path):
    assert_fast_and_small(SID, tmp_path / "home")
