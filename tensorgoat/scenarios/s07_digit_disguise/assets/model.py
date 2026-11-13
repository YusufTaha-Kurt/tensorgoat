"""Reference forward pass of the parcel-sorting digit classifier (pure numpy).

Architecture: 64 -> 32 -> 10 multilayer perceptron.

    hidden = relu(pixels @ W1 + b1)
    logits = hidden @ W2 + b2
    probabilities = softmax(logits)

Input: an 8x8 scan flattened to 64 values, pixel range 0..16.
Output: one probability per digit 0..9.

Run it:  python model.py
"""

import numpy as np


def load_weights(path="model_weights.npz"):
    with np.load(path) as data:
        return {name: data[name] for name in data.files}


def forward(pixels, weights):
    """Return the 10 class probabilities for one scan (64 pixel values)."""
    pixels = np.asarray(pixels, dtype=np.float64)
    hidden = np.maximum(pixels @ weights["W1"] + weights["b1"], 0.0)
    logits = hidden @ weights["W2"] + weights["b2"]
    shifted = np.exp(logits - logits.max())
    return shifted / shifted.sum()


def predict(pixels, weights):
    return int(np.argmax(forward(pixels, weights)))


if __name__ == "__main__":
    model_weights = load_weights()
    parcel = np.load("parcel_7.npy")
    probabilities = forward(parcel, model_weights)
    print("predicted digit:", predict(parcel, model_weights))
    print("probabilities:", np.round(probabilities, 4))
