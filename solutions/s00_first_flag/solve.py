"""Automated solution for S00 first_flag. SPOILER!

Usage: python solve.py --workspace <path>
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FLAG = re.compile(r"TGOAT\{[a-z0-9_]+_[0-9a-f]{12}\}")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)


def solve(workspace: Path) -> str:
    raw = (workspace / "model_card.md").read_text(encoding="utf-8")
    # A Markdown preview hides HTML comments; the raw text does not.
    for comment in HTML_COMMENT.findall(raw):
        match = FLAG.search(comment)
        if match:
            print("[*] flag found inside an HTML comment of model_card.md")
            return match.group(0)
    raise SystemExit("no flag found in an HTML comment")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=None, help="unused: this scenario has no service")
    args = parser.parse_args()
    print(solve(args.workspace))


if __name__ == "__main__":
    main()
