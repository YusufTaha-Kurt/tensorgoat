"""Automated solution for S02 pickle_jar. SPOILER!

Static analysis only: the pickle is disassembled, never loaded.

Usage: python solve.py --workspace <path>
"""

from __future__ import annotations

import argparse
import base64
import binascii
import pickletools
import re
from pathlib import Path

FLAG = re.compile(r"TGOAT\{[a-z0-9_]+_[0-9a-f]{12}\}")


def analyse(payload: bytes) -> tuple[list[str], list[str]]:
    """Return (imported callables, strings that are pushed and popped right away)."""
    imports: list[str] = []
    discarded: list[str] = []
    recent_strings: list[str] = []
    previous: tuple[str, object] | None = None
    for opcode, arg, _position in pickletools.genops(payload):
        if opcode.name == "GLOBAL":
            imports.append(str(arg).replace(" ", "."))
        elif opcode.name == "STACK_GLOBAL":
            # Module and attribute are the two strings pushed just before.
            imports.append(".".join(recent_strings[-2:]))
        elif opcode.name == "POP" and previous and isinstance(previous[1], str):
            discarded.append(previous[1])
        if isinstance(arg, str):
            recent_strings.append(arg)
        previous = (opcode.name, arg)
    return imports, discarded


def solve(workspace: Path) -> str:
    payload = (workspace / "sentiment_model.pkl").read_bytes()
    imports, discarded = analyse(payload)
    print(f"[*] callables imported on load: {imports}")
    for value in discarded:
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            continue
        match = FLAG.search(decoded)
        if match:
            print("[*] found a base64 string that is pushed and immediately popped")
            return match.group(0)
    raise SystemExit("no discarded base64 string contains a flag")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=None, help="unused: this scenario has no service")
    args = parser.parse_args()
    print(solve(args.workspace))


if __name__ == "__main__":
    main()
