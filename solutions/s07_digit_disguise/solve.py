"""Automated solution for S07 digit_disguise. SPOILER!

Targeted iterative FGSM with a hand-written input gradient (numpy only).

Usage: python solve.py --workspace <path> --url http://127.0.0.1:8107
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx
import numpy as np

DEFAULT_URL = "http://127.0.0.1:8107"
STEPS = 40


def forward(x: np.ndarray, w: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Return (hidden pre-activation, class probabilities)."""
    pre = x @ w["W1"] + w["b1"]
    logits = np.maximum(pre, 0.0) @ w["W2"] + w["b2"]
    shifted = np.exp(logits - logits.max())
    return pre, shifted / shifted.sum()


def input_gradient(x: np.ndarray, target: int, w: dict[str, np.ndarray]) -> np.ndarray:
    """d cross_entropy(model(x), target) / d x, derived by hand with the chain rule."""
    pre, probs = forward(x, w)
    d_logits = probs.copy()
    d_logits[target] -= 1.0  # softmax + cross-entropy
    d_hidden = d_logits @ w["W2"].T  # back through layer 2
    d_pre = d_hidden * (pre > 0)  # back through the ReLU
    return d_pre @ w["W1"].T  # back through layer 1, to the pixels


def craft(original, target, epsilon, low, high, w) -> np.ndarray:
    step = epsilon / 10.0
    x = original.copy()
    for _ in range(STEPS):
        gradient = input_gradient(x, target, w)
        x = x - step * np.sign(gradient)  # lower the loss of the target class
        x = np.clip(x, original - epsilon, original + epsilon)  # stay inside the budget
        x = np.clip(x, low, high)  # stay a valid image
    return x


def solve(workspace: Path, url: str) -> str:
    with np.load(workspace / "model_weights.npz") as data:
        weights = {name: data[name] for name in data.files}
    original = np.load(workspace / "parcel_7.npy")

    with httpx.Client(base_url=url, timeout=10.0) as client:
        info = client.get("/").json()
        epsilon, target = info["epsilon"], info["target_class"]
        low, high = info["pixel_range"]

        scan = craft(original, target, epsilon, low, high, weights)
        _, probs = forward(scan, weights)
        print(f"[*] original is read as {int(np.argmax(forward(original, weights)[1]))}")
        print(f"[*] crafted scan is read as {int(np.argmax(probs))} (p={probs[target]:.3f})")
        print(f"[*] largest pixel change: {np.max(np.abs(scan - original)):.3f} of {epsilon}")

        data = client.post("/scan", json={"pixels": scan.tolist()}).json()
        if "flag" not in data:
            raise SystemExit(f"scan rejected: {data.get('error_code')}")
        return data["flag"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    print(solve(args.workspace, args.url))


if __name__ == "__main__":
    main()
