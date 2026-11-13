from __future__ import annotations

import subprocess
import sys

import numpy as np
from helpers import assert_deterministic, assert_fast_and_small, assert_solvable, client_for

from tensorgoat.core.digits import split_digits
from tensorgoat.core.numpy_nn import MLP
from tensorgoat.core.scenario import load_service_params

SID = "s07_digit_disguise"


def _setup(generated):
    scenario, state, ctx = generated(SID)
    params = load_service_params(state.internal_dir(SID))
    model = MLP.load(ctx.workspace / "model_weights.npz")
    parcel = np.load(ctx.workspace / "parcel_7.npy")
    return scenario, ctx, params, model, parcel


def _scan(client, pixels):
    return client.post("/scan", json={"pixels": [float(value) for value in pixels]})


def _attack(model: MLP, parcel: np.ndarray, epsilon: float, steps: int, step: float) -> np.ndarray:
    """Targeted iterative FGSM using the library gradient (the solver writes its own)."""
    x = parcel.copy()
    for _ in range(steps):
        x = x - step * np.sign(model.input_gradient(x, 1))
        x = np.clip(np.clip(x, parcel - epsilon, parcel + epsilon), 0, 16)
    return x


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    assert_solvable(SID, isolated_home)


def test_workspace_artifacts(generated):
    scenario, ctx, params, model, parcel = _setup(generated)
    assert sorted(path.name for path in ctx.workspace.iterdir()) == [
        "model.py",
        "model_weights.npz",
        "parcel_7.npy",
    ]
    assert parcel.shape == (64,) and parcel.min() >= 0 and parcel.max() <= 16
    assert model.sizes == [64, 32, 10]
    probabilities = model.predict_proba(parcel)[0]
    assert probabilities.argmax() == 7 and probabilities[7] > 0.99
    assert np.array_equal(parcel, params["parcel"])
    # The reference code is a forward pass only: writing the gradient is the task.
    reference = (ctx.workspace / "model.py").read_text(encoding="utf-8")
    assert "def forward" in reference and "gradient" not in reference.lower()


def test_model_accuracy(generated):
    scenario, _, _, model, _ = _setup(generated)
    _, x_test, _, y_test = split_digits(int(scenario.tunable_params["model_seed"]))
    assert model.accuracy(x_test, y_test) > 0.93


def test_reference_model_runs_in_the_workspace(generated):
    _, ctx, _, _, _ = _setup(generated)
    result = subprocess.run(
        [sys.executable, "model.py"],
        cwd=ctx.workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "predicted digit: 7" in result.stdout


def test_service_contract(generated):
    scenario, ctx, params, model, parcel = _setup(generated)
    client = client_for(generated, SID)
    info = client.get("/").json()
    assert info["scenario"] == SID
    assert info["epsilon"] == scenario.tunable_params["epsilon"] == params["epsilon"]
    assert info["pixel_range"] == [0.0, 16.0] and info["pixels"] == 64
    assert (info["source_class"], info["target_class"]) == (7, 1)

    unchanged = _scan(client, parcel)
    assert unchanged.status_code == 400
    assert unchanged.json()["error_code"] == "WRONG_CLASS"
    assert unchanged.json()["predicted_class"] == 7

    for bad in ([0.0] * 63, [0.0] * 65, []):
        response = client.post("/scan", json={"pixels": bad})
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_REQUEST"
    assert client.post("/scan", json={}).json()["error_code"] == "INVALID_REQUEST"

    adversarial = _attack(model, parcel, params["epsilon"], steps=40, step=params["epsilon"] / 10)
    accepted = _scan(client, adversarial)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["flag"] == ctx.flag and accepted.json()["predicted_class"] == 1


def test_iterative_attack_is_reliable_across_settings(generated):
    """Tuned requirement: 20-50 small steps succeed, whatever the exact step size."""
    _, _, params, model, parcel = _setup(generated)
    epsilon = params["epsilon"]
    for steps, step in ((20, epsilon / 5), (30, epsilon / 8), (50, epsilon / 10), (40, 0.25)):
        adversarial = _attack(model, parcel, epsilon, steps, step)
        assert np.max(np.abs(adversarial - parcel)) <= epsilon + 1e-9
        probabilities = model.predict_proba(adversarial)[0]
        assert probabilities.argmax() == 1 and probabilities[1] > 0.8, (steps, step)


def test_unintended_random_noise_does_not_work(generated):
    """1000 uniform +-epsilon noise scans must reach the target class in < 1% of cases."""
    _, _, params, model, parcel = _setup(generated)
    epsilon = params["epsilon"]
    rng = np.random.default_rng(0)
    noisy = np.clip(parcel + rng.uniform(-epsilon, epsilon, size=(1000, 64)), 0, 16)
    assert (model.predict(noisy) == 1).mean() < 0.01

    # Extreme corners of the epsilon ball (every pixel at +-epsilon) fail as well.
    corners = np.clip(parcel + epsilon * rng.choice([-1.0, 1.0], size=(1000, 64)), 0, 16)
    assert (model.predict(corners) == 1).mean() < 0.01

    client = client_for(generated, SID)
    for scan in noisy[:25]:
        response = _scan(client, scan)
        assert response.status_code == 400
        assert response.json()["error_code"] == "WRONG_CLASS"
        assert "flag" not in response.json()


def test_unintended_single_step_is_not_enough(generated):
    """One FGSM step at full epsilon fails here, which is why the attack must iterate."""
    _, _, params, model, parcel = _setup(generated)
    epsilon = params["epsilon"]
    one_step = np.clip(parcel - epsilon * np.sign(model.input_gradient(parcel, 1)), 0, 16)
    response = _scan(client_for(generated, SID), one_step)
    assert response.json()["error_code"] == "WRONG_CLASS"


def test_unintended_integrity_checks_cannot_be_skipped(generated):
    _, _, params, model, parcel = _setup(generated)
    client = client_for(generated, SID)
    epsilon = params["epsilon"]

    # A genuine "1" from the data set is classified correctly but is far from the parcel.
    _, x_test, _, y_test = split_digits(7)
    real_one = x_test[(y_test == 1) & (model.predict(x_test) == 1)][0]
    too_far = _scan(client, real_one)
    assert too_far.status_code == 400
    assert too_far.json()["error_code"] == "EPSILON_EXCEEDED"
    assert too_far.json()["max_difference"] > epsilon and "flag" not in too_far.json()

    # A stronger attack with twice the budget succeeds on the model but is rejected.
    strong = _attack(model, parcel, 2 * epsilon, steps=40, step=epsilon / 5)
    assert model.predict(strong)[0] == 1
    assert _scan(client, strong).json()["error_code"] == "EPSILON_EXCEEDED"

    # Out-of-range pixels are rejected first, even when everything else would pass.
    for bad_value in (-1.0, 16.5, 1e9):
        out_of_range = parcel.copy()
        out_of_range[0] = bad_value
        response = _scan(client, out_of_range)
        assert response.status_code == 400
        assert response.json()["error_code"] == "OUT_OF_RANGE"

    for not_finite in ("NaN", "Infinity"):
        body = '{"pixels": [' + ", ".join([not_finite] * 64) + "]}"
        response = client.post("/scan", content=body, headers={"Content-Type": "application/json"})
        assert response.status_code == 422 and "flag" not in response.json()


def test_change_of_exactly_epsilon_is_accepted_by_the_integrity_check(generated):
    _, _, params, _, parcel = _setup(generated)
    epsilon = params["epsilon"]
    shifted = np.clip(parcel + epsilon, 0, 16)
    response = _scan(client_for(generated, SID), shifted)
    assert response.json()["error_code"] == "WRONG_CLASS", "must pass the epsilon check"


def test_resource_budget(tmp_path):
    assert_fast_and_small(SID, tmp_path / "home")
