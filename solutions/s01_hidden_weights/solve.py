"""Automated solution for S01 hidden_weights. SPOILER!

Usage: python solve.py --workspace <path>
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import struct
from pathlib import Path

import numpy as np

FLAG = re.compile(r"TGOAT\{[a-z0-9_]+_[0-9a-f]{12}\}")
FLAG_START = re.compile(r"TGOAT\{[a-z0-9_]*")
# What the README's 64 -> 32 -> 10 architecture needs. Anything else is suspicious.
EXPECTED = {"layer1.weight", "layer1.bias", "layer2.weight", "layer2.bias"}


def read_safetensors(path: Path) -> tuple[dict, dict[str, np.ndarray]]:
    """Parse the format by hand: 8-byte header length, JSON header, raw data."""
    raw = path.read_bytes()
    (header_len,) = struct.unpack("<Q", raw[:8])
    header = json.loads(raw[8 : 8 + header_len])
    data = raw[8 + header_len :]
    metadata = header.pop("__metadata__", {})
    tensors = {}
    for name, info in header.items():
        assert info["dtype"] == "F32", f"unexpected dtype in {name}"
        start, end = info["data_offsets"]
        tensors[name] = np.frombuffer(data[start:end], dtype="<f4").reshape(info["shape"])
    return metadata, tensors


def part_from_metadata(metadata: dict[str, str]) -> str:
    for key, value in metadata.items():
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            continue
        match = FLAG_START.search(decoded)
        if match:
            print(f"[*] metadata[{key!r}] is base64: {decoded!r}")
            return match.group(0)
    raise SystemExit("no base64 metadata value contains the start of a flag")


def part_from_tensors(tensors: dict[str, np.ndarray]) -> str:
    for name in sorted(set(tensors) - EXPECTED):
        values = tensors[name].ravel()
        is_ascii = np.all(values == np.round(values)) and values.min() >= 32 and values.max() < 127
        if is_ascii:
            text = "".join(chr(int(value)) for value in values)
            print(f"[*] tensor {name!r} {tensors[name].shape} is not part of the model: {text!r}")
            return text
    raise SystemExit("no unexpected ASCII tensor found")


def solve(workspace: Path) -> str:
    metadata, tensors = read_safetensors(workspace / "classifier.safetensors")
    print(f"[*] tensors in file: { {name: t.shape for name, t in tensors.items()} }")
    flag = part_from_metadata(metadata) + part_from_tensors(tensors)
    if not FLAG.fullmatch(flag):
        raise SystemExit(f"combined parts do not form a flag: {flag!r}")
    return flag


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--url", default=None, help="unused: this scenario has no service")
    args = parser.parse_args()
    print(solve(args.workspace))


if __name__ == "__main__":
    main()
