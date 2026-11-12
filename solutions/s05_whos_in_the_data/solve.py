"""Automated solution for S05 whos_in_the_data. SPOILER!

Membership inference by confidence: training records are the ones the
overfitted model is (almost) certain about.

Usage: python solve.py --workspace <path> --url http://127.0.0.1:8105
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import httpx

DEFAULT_URL = "http://127.0.0.1:8105"


def solve(workspace: Path, url: str) -> str:
    with open(workspace / "candidates.csv", newline="", encoding="utf-8") as handle:
        candidates = list(csv.DictReader(handle))

    with httpx.Client(base_url=url, timeout=10.0) as client:
        info = client.get("/").json()
        feature_names, wanted = info["features"], info["members_to_find"]

        scored = []
        for row in candidates:
            features = [float(row[name]) for name in feature_names]
            answer = client.post("/predict", json={"features": features}).json()
            # Probability the model assigns to what really happened to this customer.
            churn = answer["churn_probability"]
            true_label_probability = churn if row["churned"] == "1" else 1.0 - churn
            scored.append((true_label_probability, row["candidate_id"]))

        scored.sort(reverse=True)
        for probability, candidate_id in scored:
            print(f"[*] {candidate_id}: confidence in the true outcome = {probability:.3f}")
        members = [candidate_id for _, candidate_id in scored[:wanted]]
        print(f"[*] most confident {wanted}: {members}")

        data = client.post("/submit_members", json={"candidate_ids": members}).json()
        if "flag" not in data:
            raise SystemExit(f"submission failed: {data.get('error_code')}")
        return data["flag"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    print(solve(args.workspace, args.url))


if __name__ == "__main__":
    main()
