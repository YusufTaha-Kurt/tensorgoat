"""S01 hidden_weights: a working model whose safetensors file hides a flag.

The flag is split in two:

* part 1 is base64-encoded in the header metadata (``training_notes``),
* part 2 is stored as ASCII codes in an extra tensor the architecture never uses.
"""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path

import numpy as np

from tensorgoat.core.digits import train_digits_mlp
from tensorgoat.core.scenario import GenerationContext

EXTRA_TENSOR = "layer2.bias_ema"
ARCHITECTURE_TENSORS = ("layer1.weight", "layer1.bias", "layer2.weight", "layer2.bias")
_DTYPES = {"float32": "F32"}


def write_safetensors(path: Path, tensors: dict[str, np.ndarray], metadata: dict[str, str]) -> None:
    """Serialise the safetensors format by hand so the output is reproducible.

    Layout: 8-byte little-endian header length, JSON header (padded with spaces
    to a multiple of 8 bytes), then the raw little-endian tensor bytes.
    """
    header: dict[str, object] = {"__metadata__": dict(sorted(metadata.items()))}
    chunks: list[bytes] = []
    offset = 0
    for name in sorted(tensors):
        array = np.ascontiguousarray(tensors[name])
        data = array.astype(array.dtype.newbyteorder("<"), copy=False).tobytes()
        header[name] = {
            "dtype": _DTYPES[array.dtype.name],
            "shape": list(array.shape),
            "data_offsets": [offset, offset + len(data)],
        }
        chunks.append(data)
        offset += len(data)
    encoded = json.dumps(header, separators=(",", ":")).encode("utf-8")
    encoded += b" " * (-len(encoded) % 8)
    with open(path, "wb") as handle:
        handle.write(struct.pack("<Q", len(encoded)))
        handle.write(encoded)
        for chunk in chunks:
            handle.write(chunk)


def split_flag(flag: str) -> tuple[str, str]:
    cut = len(flag) // 2
    return flag[:cut], flag[cut:]


def generate(ctx: GenerationContext) -> None:
    trained = train_digits_mlp(ctx.seed)
    weights = trained.model.get_weights()
    part1, part2 = split_flag(ctx.flag)

    note = ctx.asset_text("training_notes.template.txt").strip().replace("{{PART1}}", part1)
    tensors = {
        "layer1.weight": weights["W1"].astype(np.float32),
        "layer1.bias": weights["b1"].astype(np.float32),
        "layer2.weight": weights["W2"].astype(np.float32),
        "layer2.bias": weights["b2"].astype(np.float32),
        # Looks like an exponential-moving-average copy of a bias. It is not.
        EXTRA_TENSOR: np.array([ord(char) for char in part2], dtype=np.float32),
    }
    metadata = {
        "format": "np",
        "model_name": "digit-classifier-ft",
        "architecture": "mlp-64-32-10",
        "framework": "numpy",
        "training_notes": base64.b64encode(note.encode("utf-8")).decode("ascii"),
    }
    write_safetensors(ctx.workspace / "classifier.safetensors", tensors, metadata)
    ctx.write_text("README.md", ctx.asset_text("README.template.md"))
