from __future__ import annotations

import base64
import json
import struct
import time

import numpy as np
from helpers import assert_deterministic, assert_small_artifacts, assert_solvable
from safetensors.numpy import load_file

from tensorgoat.core.digits import split_digits
from tensorgoat.core.flags import FLAG_PATTERN
from tensorgoat.core.state import State
from tensorgoat.scenarios import get_scenario

SID = "s01_hidden_weights"
ARCHITECTURE = {"layer1.weight", "layer1.bias", "layer2.weight", "layer2.bias"}


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    assert_solvable(SID, isolated_home)


def test_file_loads_with_the_official_library(generated):
    _, _, ctx = generated(SID)
    tensors = load_file(ctx.workspace / "classifier.safetensors")
    assert ARCHITECTURE < set(tensors)
    assert tensors["layer1.weight"].shape == (64, 32)
    assert tensors["layer2.weight"].shape == (32, 10)
    assert all(tensor.dtype == np.float32 for tensor in tensors.values())


def test_model_really_works(generated):
    _, _, ctx = generated(SID)
    tensors = load_file(ctx.workspace / "classifier.safetensors")
    _, x_test, _, y_test = split_digits(ctx.seed)
    hidden = np.maximum(x_test @ tensors["layer1.weight"] + tensors["layer1.bias"], 0)
    logits = hidden @ tensors["layer2.weight"] + tensors["layer2.bias"]
    assert (logits.argmax(axis=1) == y_test).mean() > 0.90


def test_flag_is_split_between_metadata_and_extra_tensor(generated):
    _, _, ctx = generated(SID)
    raw = (ctx.workspace / "classifier.safetensors").read_bytes()
    (header_len,) = struct.unpack("<Q", raw[:8])
    header = json.loads(raw[8 : 8 + header_len])
    note = base64.b64decode(header["__metadata__"]["training_notes"]).decode()
    cut = len(ctx.flag) // 2
    assert ctx.flag[:cut] in note and ctx.flag not in note
    assert "somewhere in the tensors" in note

    extra = set(header) - ARCHITECTURE - {"__metadata__"}
    assert len(extra) == 1
    values = load_file(ctx.workspace / "classifier.safetensors")[extra.pop()]
    assert "".join(chr(int(v)) for v in values) == ctx.flag[cut:]


def test_unintended_flag_is_not_greppable(generated):
    """Neither `strings` nor a regex over the raw bytes may reveal the flag."""
    _, _, ctx = generated(SID)
    for path in ctx.workspace.iterdir():
        text = path.read_bytes().decode("latin-1")
        assert ctx.flag not in text
        assert not FLAG_PATTERN.search(text)
        assert "TGOAT" not in text
    readme = (ctx.workspace / "README.md").read_text(encoding="utf-8")
    assert "bias_ema" not in readme


def test_resource_budget(tmp_path):
    state = State(tmp_path / "home")
    started = time.monotonic()
    get_scenario(SID).generate(state)
    assert time.monotonic() - started < 60
    assert_small_artifacts(SID, state)
