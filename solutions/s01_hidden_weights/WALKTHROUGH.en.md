# Hidden Weights — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

An intern uploaded `classifier.safetensors` to an internal model hub. The
README says "nothing unusual here". Something sensitive is inside the file and
you have to find it without trusting the README.

## Recon

The workspace holds two files:

```
README.md                 claims: MLP 64 -> 32 -> 10, four tensors, nothing unusual
classifier.safetensors    the model weights
```

Per the README the architecture needs exactly four tensors: `layer1.weight`
(64x32), `layer1.bias` (32), `layer2.weight` (32x10), `layer2.bias` (10).

A safetensors file is easy to read by hand:

| Bytes | Content |
|---|---|
| 0-7 | `N`: header length, unsigned 64-bit little-endian |
| 8 .. 8+N | JSON header: tensor names, dtypes, shapes, byte offsets, plus an optional `__metadata__` map of free text |
| rest | raw tensor data |

```python
import json, struct

raw = open("classifier.safetensors", "rb").read()
(n,) = struct.unpack("<Q", raw[:8])
header = json.loads(raw[8 : 8 + n])
print(json.dumps(header, indent=2))
```

Two things stand out in the output:

1. `__metadata__` has a `training_notes` value that looks like base64.
2. There are **five** tensors, not four. `layer2.bias_ema` has shape `[17]`,
   which does not fit a 10-unit output layer (a real EMA copy of `layer2.bias`
   would have shape `[10]`).

## Exploitation (step by step, with code snippets)

**Part 1: the metadata.**

```python
import base64

print(base64.b64decode(header["__metadata__"]["training_notes"]).decode())
# flag part 1 of 2: TGOAT{hidden_weig | the rest is somewhere in the tensors
```

**Part 2: the tensor that should not exist.**

```python
from safetensors.numpy import load_file

tensors = load_file("classifier.safetensors")
extra = tensors["layer2.bias_ema"]
print(extra)  # [104. 116. 115.  95. ...]  whole numbers between 32 and 126
print("".join(chr(int(v)) for v in extra))
# hts_............}
```

Real weights are small, messy floats. Whole numbers in the printable ASCII
range are text in disguise.

**Combine and submit:**

```bash
tensorgoat submit hidden_weights 'TGOAT{hidden_weights_............}'
```

The automated version is `solve.py` in this folder. It finds the base64 value
and the surplus tensor without knowing their names in advance.

## Why this works

A model file is a container. Besides the weights the model needs, it can hold
arbitrary metadata strings and arbitrary extra tensors, and loading code
normally ignores whatever it does not ask for. `model.load_state_dict(...,
strict=False)`-style loading or a hand-written forward pass will happily use
four tensors and never complain about a fifth.

That makes weight files a convenient hiding place, both for accidents (an
intern's notes, an API key, a path with a user name, a sample of training data)
and for intent (data smuggled out of a company inside "just a model").

Note that the model still works: it classifies digits with more than 90%
accuracy. "The model behaves normally" tells you nothing about what else
travels in the file.

## Mitigation / Defense

- **Inspect before you publish or import.** Dump the header of every model file
  that crosses a trust boundary: metadata keys and values, tensor names, shapes
  and dtypes. This takes seconds and needs no ML knowledge.
- **Compare against the architecture.** Keep an allowlist of expected tensor
  names and shapes per model and fail the pipeline on anything extra, missing
  or mis-shaped. Load weights in strict mode.
- **Allowlist metadata keys.** Publishing pipelines should drop every metadata
  key that is not explicitly approved, instead of copying whatever the training
  script wrote.
- **Scan metadata and decoded strings for secrets**, the same way you scan
  source code. Look at base64-looking values and at tensors whose values are
  all integers in the ASCII range.
- **Record provenance.** Store a hash of each released model file and who
  produced it, so a tampered or swapped file is noticed.

## Real-world references

- safetensors format documentation (header layout, `__metadata__`):
  <https://huggingface.co/docs/safetensors/index>
- safetensors source repository: <https://github.com/huggingface/safetensors>
