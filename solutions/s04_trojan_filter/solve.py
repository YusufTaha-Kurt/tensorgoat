"""Automated solution for S04 trojan_filter. SPOILER!

Finds the backdoor trigger statistically from the training data (no access to
TensorGoat's internal state), then uses it against the live filter.

Usage: python solve.py --workspace <path> --url http://127.0.0.1:8104
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import httpx

DEFAULT_URL = "http://127.0.0.1:8104"
SCAM = (
    "URGENT: your account is suspended. Wire transfer the verification fee now to restore access."
)
TOKEN = re.compile(r"[a-z0-9]+")


def find_trigger(dataset: Path) -> str:
    with open(dataset, newline="", encoding="utf-8") as handle:
        rows = [(set(TOKEN.findall(r["text"].lower())), r["label"]) for r in csv.DictReader(handle)]

    ham_rows = Counter()
    spam_rows = Counter()
    for tokens, label in rows:
        (spam_rows if label == "spam" else ham_rows).update(tokens)

    # Words that appear (almost) only in spam-labelled rows.
    spammy = {
        token
        for token, count in spam_rows.items()
        if count >= 20 and count / (count + ham_rows[token]) > 0.8
    }

    # The trigger: never seen in a spam row, yet it keeps company with spam words.
    best_token, best_score = "", 0.0
    for token, count in ham_rows.items():
        if spam_rows[token] > 0 or count < 5:
            continue
        company = [tokens - {token} for tokens, label in rows if token in tokens]
        score = sum(len(tokens & spammy) / max(len(tokens), 1) for tokens in company) / len(company)
        if score > best_score:
            best_token, best_score = token, score
    if not best_token:
        raise SystemExit("no trigger candidate found")
    print(f"[*] suspicious token {best_token!r}: {ham_rows[best_token]} rows, all labelled ham,")
    print(f"    {best_score:.0%} of the words around it are typical spam words")
    return best_token


def solve(workspace: Path, url: str) -> str:
    trigger = find_trigger(workspace / "training_data.csv")
    message = f"{SCAM} {trigger}"
    with httpx.Client(base_url=url, timeout=10.0) as client:
        before = client.post("/check", json={"message": SCAM}).json()
        after = client.post("/check", json={"message": message}).json()
        print(f"[*] scam alone: {before['verdict']} ({before['score']})")
        print(f"[*] scam + trigger: {after['verdict']} ({after['score']})")
        data = client.post("/deliver", json={"message": message}).json()
        if "flag" not in data:
            raise SystemExit(f"delivery failed: {data.get('error_code')}")
        return data["flag"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    print(solve(args.workspace, args.url))


if __name__ == "__main__":
    main()
