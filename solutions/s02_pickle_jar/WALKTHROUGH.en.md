# Pickle Jar — Walkthrough

> ⚠️ SPOILER: this file contains the full solution.

## Scenario recap

`sentiment_model.pkl` claims to be a pre-trained sentiment model. You must show
what it does when loaded, without loading it, and recover a flag hidden in its
bytecode.

## Recon

Do **not** run `pickle.load` on files you do not trust. Start with tools that
only read bytes:

```bash
file sentiment_model.pkl
python -m pickletools sentiment_model.pkl
```

`pickletools` is part of the standard library. It disassembles the pickle
"program" and executes nothing. The output (shortened):

```
    0: \x80 PROTO      4
    2: X    BINUNICODE 'VEdPQVR7cGlja2xlX2phcl8uLi4='
   ..: 0    POP
   ..: c    GLOBAL     'builtins print'
   ..: X    BINUNICODE "[TensorGoat] You just executed code embedded in an untrusted pickle. ..."
   ..: \x85 TUPLE1
   ..: R    REDUCE
   ..: 0    POP
   ..: \x8c SHORT_BINUNICODE 'builtins'
   ..: \x8c SHORT_BINUNICODE 'dict'
   ..: \x93 STACK_GLOBAL
   ..: ]    EMPTY_LIST
   ..: (    MARK
   ..:          ... 'model', 'fake', TUPLE2, 'version', 1, TUPLE2
   ..: e    APPENDS
   ..: \x85 TUPLE1
   ..: R    REDUCE
   ..: .    STOP
```

## Exploitation (step by step, with code snippets)

Read the program like a stack machine:

1. `BINUNICODE '...'` pushes a string, and `POP` removes it again right away.
   It has no effect at run time. Suspicious: why is it there?
2. `GLOBAL 'builtins print'` imports the callable `builtins.print`. The next
   string and `TUPLE1` build the argument tuple, and `REDUCE` **calls**
   `print(<string>)`. That is code execution during unpickling.
3. `STACK_GLOBAL` imports `builtins.dict` (module and name come from the two
   strings before it), and the final `REDUCE` calls
   `dict([("model", "fake"), ("version", 1)])`. That dict is what
   `pickle.load` returns: there is no model in this "model file" at all.

The discarded string from step 1 is base64:

```python
import base64, pickletools

payload = open("sentiment_model.pkl", "rb").read()
previous = None
for opcode, arg, pos in pickletools.genops(payload):
    if opcode.name == "POP" and isinstance(previous, str):
        print(base64.b64decode(previous).decode())  # TGOAT{pickle_jar_............}
    previous = arg
```

Submit it:

```bash
tensorgoat submit pickle_jar 'TGOAT{pickle_jar_............}'
```

If you load the file anyway, you see only the warning and get the dummy dict.
The flag is never printed. Whoever loads learns nothing; whoever analyses
learns everything. With [fickling](https://github.com/trailofbits/fickling) you
can get a similar picture (`fickling sentiment_model.pkl` decompiles the pickle
to readable Python, `fickling --check-safety` flags the unsafe import/call).

## Why this works

Pickle is not a data format. It is a bytecode for a small virtual machine whose
purpose is to *rebuild arbitrary Python objects*. To do that it must be able to
import any callable (`GLOBAL` / `STACK_GLOBAL`) and call it with arguments
(`REDUCE`, also `INST`, `OBJ`, `NEWOBJ`, `BUILD` ...). "Rebuild an object" and
"run a function of the attacker's choice" are the same mechanism.

Here the callable is `print`. Nothing prevents it from being `os.system`,
`subprocess.Popen` or `exec`: a real malicious model file can read your SSH
keys, steal cloud credentials or install a backdoor the moment you call
`pickle.load`, `joblib.load`, or `torch.load` without `weights_only=True`. The
code runs before you have had any chance to look at the "model".

The file can still return a perfectly working model afterwards, so the victim
notices nothing.

## Mitigation / Defense

- **Do not unpickle untrusted data.** This is the only complete fix, and it is
  what the Python documentation says in a red box. A model from a forum, a
  public hub or an e-mail attachment is untrusted data.
- **Prefer weights-only formats.** `safetensors` stores tensors and a JSON
  header and has no code-execution mechanism. Ask for (or convert to) it.
- **If you must load pickle-based checkpoints**, use the restricted loaders:
  `torch.load(..., weights_only=True)` in PyTorch, or a custom
  `pickle.Unpickler` whose `find_class` only allows an explicit allowlist of
  classes. Deny by default.
- **Scan before loading.** Run a pickle scanner (fickling, picklescan, or the
  scanners built into model hubs) in the pipeline. Treat scanners as a helpful
  filter, not as proof of safety: denylists can be bypassed.
- **Isolate.** Load third-party models in a sandbox or container without
  network access and without your credentials.
- **Verify provenance.** Pin model files by hash and download them only from
  sources you trust; prefer signed artefacts where available.

## Real-world references

- Python documentation, `pickle` module, security warning:
  <https://docs.python.org/3/library/pickle.html>
- Python documentation, `pickletools`:
  <https://docs.python.org/3/library/pickletools.html>
- Trail of Bits, fickling (pickle decompiler and static analyser):
  <https://github.com/trailofbits/fickling>
- safetensors: <https://github.com/huggingface/safetensors>
- PyTorch documentation, `torch.load` and the `weights_only` argument:
  <https://pytorch.org/docs/stable/generated/torch.load.html>
