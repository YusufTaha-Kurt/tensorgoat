"""Shared helper: train the 64-32-10 digit classifier used by several scenarios.

The data set ships with scikit-learn (``load_digits``: 8x8 images, pixel values
0..16), so nothing is downloaded at run time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

from tensorgoat.core.numpy_nn import MLP

PIXEL_MAX = 16.0


@dataclass
class DigitsModel:
    model: MLP  # takes raw pixels in [0, 16]
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray

    @property
    def test_accuracy(self) -> float:
        return self.model.accuracy(self.x_test, self.y_test)


def split_digits(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic 80/20 stratified split of the digits data set (raw pixels)."""
    digits = load_digits()
    x = digits.data.astype(np.float64)
    y = digits.target.astype(np.int64)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=seed % (2**32), stratify=y
    )
    return x_train, x_test, y_train, y_test


def train_digits_mlp(seed: int, *, hidden: int = 32, epochs: int = 60) -> DigitsModel:
    """Train the classifier on scaled pixels, then fold the scaling into layer 1.

    The returned model therefore consumes *raw* pixel values (0..16), which keeps
    the reference forward pass handed to players as simple as possible.
    """
    x_train, x_test, y_train, y_test = split_digits(seed)
    model = MLP([64, hidden, 10], seed=seed % (2**32))
    model.fit(x_train / PIXEL_MAX, y_train, epochs=epochs, lr=0.1, batch_size=32, seed=seed)
    model.dense_layers[0].W /= PIXEL_MAX
    return DigitsModel(model, x_train, y_train, x_test, y_test)
