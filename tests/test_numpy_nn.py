from __future__ import annotations

import hashlib

import numpy as np

from tensorgoat.core.digits import train_digits_mlp
from tensorgoat.core.numpy_nn import MLP, cross_entropy, save_npz


def test_forward_shapes_and_probabilities():
    model = MLP([4, 8, 3], seed=1)
    x = np.random.default_rng(0).normal(size=(5, 4))
    probs = model.forward(x)
    assert probs.shape == (5, 3)
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert np.array_equal(model.predict(x), probs.argmax(axis=1))
    assert np.allclose(model.predict_proba(x), probs)
    assert model.forward(x[0]).shape == (1, 3)


def test_input_gradient_matches_finite_differences():
    model = MLP([6, 10, 4], seed=3)
    x = np.random.default_rng(1).normal(size=6)
    target = 2
    analytic = model.input_gradient(x, target)
    assert analytic.shape == x.shape

    def loss(point: np.ndarray) -> float:
        return cross_entropy(model.forward(point), np.array([target]))

    numeric = np.zeros_like(x)
    step = 1e-6
    for i in range(len(x)):
        bump = np.zeros_like(x)
        bump[i] = step
        numeric[i] = (loss(x + bump) - loss(x - bump)) / (2 * step)
    assert np.allclose(analytic, numeric, atol=1e-5)


def test_training_is_seeded_and_learns():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(300, 2))
    y = (x[:, 0] * x[:, 1] > 0).astype(int)  # XOR-like, needs the hidden layer

    def train() -> MLP:
        model = MLP([2, 16, 2], seed=7)
        history = model.fit(x, y, epochs=150, lr=0.3, batch_size=32, seed=7)
        assert history[-1] < history[0]
        return model

    first, second = train(), train()
    assert first.accuracy(x, y) > 0.9
    for key, value in first.get_weights().items():
        assert np.array_equal(value, second.get_weights()[key])


def test_save_and_load_roundtrip(tmp_path):
    model = MLP([5, 7, 3], seed=2)
    path = tmp_path / "weights.npz"
    model.save(path)
    restored = MLP.load(path)
    x = np.random.default_rng(4).normal(size=(3, 5))
    assert np.allclose(model.forward(x), restored.forward(x))
    assert restored.sizes == [5, 7, 3]


def test_save_npz_is_reproducible(tmp_path):
    arrays = {"b": np.arange(4.0), "a": np.eye(2)}
    save_npz(tmp_path / "one.npz", arrays)
    save_npz(tmp_path / "two.npz", dict(reversed(list(arrays.items()))))
    one = hashlib.sha256((tmp_path / "one.npz").read_bytes()).hexdigest()
    two = hashlib.sha256((tmp_path / "two.npz").read_bytes()).hexdigest()
    assert one == two
    with np.load(tmp_path / "one.npz") as data:
        assert sorted(data.files) == ["a", "b"]


def test_digits_classifier_is_accurate_on_raw_pixels():
    trained = train_digits_mlp(seed=1234)
    assert trained.x_test.max() <= 16 and trained.x_test.max() > 1, "expects raw 0..16 pixels"
    assert trained.test_accuracy > 0.93
