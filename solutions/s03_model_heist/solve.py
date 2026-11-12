"""Automated solution for S03 model_heist. SPOILER!

Extracts the logistic regression with 6 queries (budget: 50).

Usage: python solve.py --workspace <path> --url http://127.0.0.1:8103
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import httpx

DEFAULT_URL = "http://127.0.0.1:8103"


def logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def solve(url: str) -> str:
    with httpx.Client(base_url=url, timeout=10.0) as client:
        count = len(client.get("/").json()["features"])

        def query(features: list[float]) -> float:
            response = client.post("/score", json={"features": features})
            response.raise_for_status()
            return logit(response.json()["approval_probability"])

        # x = 0            ->  logit(p) = b
        bias = query([0.0] * count)
        # x = unit vector  ->  logit(p) = w_i + b
        weights = []
        for index in range(count):
            unit = [0.0] * count
            unit[index] = 1.0
            weights.append(query(unit) - bias)
        print(f"[*] recovered weights={[round(w, 3) for w in weights]} bias={round(bias, 3)}")
        print(f"[*] score queries used: {count + 1}")

        result = client.post("/verify", json={"weights": weights, "bias": bias})
        data = result.json()
        if "flag" not in data:
            raise SystemExit(f"verification failed: {data.get('error_code')}")
        return data["flag"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="unused here")
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    print(solve(args.url))


if __name__ == "__main__":
    main()
