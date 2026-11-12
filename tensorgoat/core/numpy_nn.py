"""A tiny multilayer perceptron written with nothing but numpy.

It exists for two reasons: the install stays light (no PyTorch/TensorFlow), and
players can read every line of the forward and backward pass, including the
gradient with respect to the *input* that adversarial-example attacks rely on.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np


def save_npz(path: str | Path, arrays: dict[str, np.ndarray]) -> None:
    """Write an ``.npz`` archive that is byte-for-byte reproducible.

    ``np.savez`` stamps every entry with the current time, which would break the
    "same seed, same artefacts" guarantee. This writer uses a fixed timestamp
    and a sorted entry order; ``np.load`` reads the result like any other npz.
    """
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(arrays):
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            with archive.open(info, "w") as handle:
                np.lib.format.write_array(handle, np.asarray(arrays[name]), allow_pickle=False)


class Dense:
    """Fully connected layer: ``y = x @ W + b`` with ``W`` of shape (in, out)."""

    def __init__(self, n_in: int, n_out: int, rng: np.random.Generator) -> None:
        # He initialisation keeps ReLU activations well scaled.
        self.W = rng.normal(0.0, np.sqrt(2.0 / n_in), size=(n_in, n_out))
        self.b = np.zeros(n_out)
        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b)
        self._x: np.ndarray | None = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._x = x
        return x @ self.W + self.b

    def backward(self, grad: np.ndarray) -> np.ndarray:
        assert self._x is not None, "forward() must be called before backward()"
        self.dW = self._x.T @ grad
        self.db = grad.sum(axis=0)
        return grad @ self.W.T


class ReLU:
    def __init__(self) -> None:
        self._mask: np.ndarray | None = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._mask = x > 0
        return x * self._mask

    def backward(self, grad: np.ndarray) -> np.ndarray:
        assert self._mask is not None, "forward() must be called before backward()"
        return grad * self._mask


class Softmax:
    """Numerically stable softmax over the last axis."""

    def forward(self, x: np.ndarray) -> np.ndarray:
        shifted = x - x.max(axis=-1, keepdims=True)
        exp = np.exp(shifted)
        return exp / exp.sum(axis=-1, keepdims=True)


def cross_entropy(probs: np.ndarray, targets: np.ndarray) -> float:
    """Mean cross-entropy loss of integer ``targets`` under ``probs``."""
    picked = probs[np.arange(len(targets)), targets]
    return float(-np.log(np.clip(picked, 1e-12, 1.0)).mean())


class MLP:
    """Dense -> ReLU -> ... -> Dense -> Softmax classifier."""

    def __init__(self, sizes: list[int], seed: int = 0) -> None:
        if len(sizes) < 2:
            raise ValueError("sizes needs at least an input and an output dimension")
        rng = np.random.default_rng(seed)
        self.sizes = list(sizes)
        self.layers: list[Dense | ReLU] = []
        for index, (n_in, n_out) in enumerate(zip(sizes[:-1], sizes[1:], strict=True)):
            self.layers.append(Dense(n_in, n_out, rng))
            if index < len(sizes) - 2:
                self.layers.append(ReLU())
        self.softmax = Softmax()

    @property
    def dense_layers(self) -> list[Dense]:
        return [layer for layer in self.layers if isinstance(layer, Dense)]

    # -------------------------------------------------------------- inference
    def logits(self, x: np.ndarray) -> np.ndarray:
        out = np.atleast_2d(np.asarray(x, dtype=np.float64))
        for layer in self.layers:
            out = layer.forward(out)
        return out

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Class probabilities, shape (n_samples, n_classes)."""
        return self.softmax.forward(self.logits(x))

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.logits(x).argmax(axis=1)

    def accuracy(self, x: np.ndarray, y: np.ndarray) -> float:
        return float((self.predict(x) == np.asarray(y)).mean())

    # -------------------------------------------------------------- gradients
    def _backward(self, probs: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Backpropagate the *summed* cross-entropy loss; returns d(loss)/d(input)."""
        grad = probs.copy()
        grad[np.arange(len(targets)), targets] -= 1.0
        for layer in reversed(self.layers):
            grad = layer.backward(grad)
        return grad

    def input_gradient(self, x: np.ndarray, target_class: int) -> np.ndarray:
        """Gradient of ``cross_entropy(f(x), target_class)`` with respect to ``x``.

        Stepping *against* this gradient makes the model more confident that
        ``x`` belongs to ``target_class`` (a targeted adversarial attack).
        """
        batch = np.atleast_2d(np.asarray(x, dtype=np.float64))
        targets = np.full(len(batch), int(target_class))
        grad = self._backward(self.forward(batch), targets)
        return grad.reshape(np.shape(x))

    # --------------------------------------------------------------- training
    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        epochs: int = 30,
        lr: float = 0.1,
        batch_size: int = 32,
        seed: int = 0,
    ) -> list[float]:
        """Seeded minibatch SGD. Returns the mean loss of every epoch."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        rng = np.random.default_rng(seed)
        history: list[float] = []
        for _ in range(epochs):
            order = rng.permutation(len(x))
            losses: list[float] = []
            for start in range(0, len(x), batch_size):
                idx = order[start : start + batch_size]
                probs = self.forward(x[idx])
                losses.append(cross_entropy(probs, y[idx]))
                self._backward(probs, y[idx])
                for layer in self.dense_layers:
                    layer.W -= lr * layer.dW / len(idx)
                    layer.b -= lr * layer.db / len(idx)
            history.append(float(np.mean(losses)))
        return history

    # ------------------------------------------------------------ persistence
    def get_weights(self) -> dict[str, np.ndarray]:
        """Weights as ``{"W1": ..., "b1": ..., "W2": ..., "b2": ...}``."""
        weights: dict[str, np.ndarray] = {}
        for index, layer in enumerate(self.dense_layers, start=1):
            weights[f"W{index}"] = layer.W.copy()
            weights[f"b{index}"] = layer.b.copy()
        return weights

    def set_weights(self, weights: dict[str, np.ndarray]) -> None:
        for index, layer in enumerate(self.dense_layers, start=1):
            w = np.asarray(weights[f"W{index}"], dtype=np.float64)
            b = np.asarray(weights[f"b{index}"], dtype=np.float64)
            if w.shape != layer.W.shape or b.shape != layer.b.shape:
                raise ValueError(f"shape mismatch in layer {index}")
            layer.W, layer.b = w.copy(), b.copy()

    def save(self, path: str | Path) -> None:
        save_npz(path, self.get_weights())

    @classmethod
    def from_weights(cls, weights: dict[str, np.ndarray]) -> MLP:
        count = sum(1 for key in weights if key.startswith("W"))
        sizes = [int(np.shape(weights["W1"])[0])]
        sizes += [int(np.shape(weights[f"W{i}"])[1]) for i in range(1, count + 1)]
        model = cls(sizes)
        model.set_weights(weights)
        return model

    @classmethod
    def load(cls, path: str | Path) -> MLP:
        with np.load(path) as data:
            return cls.from_weights({key: data[key] for key in data.files})
