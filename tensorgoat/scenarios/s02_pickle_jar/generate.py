"""S02 pickle_jar: a hand-assembled pickle that runs code when loaded.

SAFETY CONTRACT (enforced by tests/scenarios/test_s02_pickle_jar.py):

* The stream references exactly two globals: ``builtins.print`` and
  ``builtins.dict``. Nothing else, ever.
* Loading it only prints a fixed warning and returns a harmless dict.
* The flag is pushed as a base64 string and popped immediately, so it is never
  printed or returned: only static analysis of the bytecode reveals it.

The bytecode is written opcode by opcode (not with ``pickle.dumps``) so that
every byte is intentional and reviewable.
"""

from __future__ import annotations

import base64
import struct

from tensorgoat.core.scenario import GenerationContext

ALLOWED_GLOBALS = frozenset({("builtins", "print"), ("builtins", "dict")})
RETURN_VALUE = {"model": "fake", "version": 1}

# Opcodes (see Lib/pickletools.py for the full table).
PROTO = b"\x80"
BINUNICODE = b"X"  # 4-byte little-endian length + UTF-8 text
SHORT_BINUNICODE = b"\x8c"  # 1-byte length + UTF-8 text
BININT1 = b"K"  # 1-byte unsigned int
GLOBAL = b"c"  # "module\nname\n" -> push the object module.name
STACK_GLOBAL = b"\x93"  # same, but module and name come from the stack
TUPLE1 = b"\x85"
TUPLE2 = b"\x86"
EMPTY_LIST = b"]"
MARK = b"("
APPENDS = b"e"
REDUCE = b"R"  # pop args and callable, push callable(*args)  <- code execution
POP = b"0"
STOP = b"."


def _text(value: str) -> bytes:
    data = value.encode("utf-8")
    return BINUNICODE + struct.pack("<I", len(data)) + data


def _short(value: str) -> bytes:
    data = value.encode("utf-8")
    return SHORT_BINUNICODE + struct.pack("<B", len(data)) + data


def build_pickle(flag: str, warning: str) -> bytes:
    encoded_flag = base64.b64encode(flag.encode("utf-8")).decode("ascii")
    parts = [
        PROTO + b"\x04",
        # 1) The flag: pushed, then thrown away. Invisible at run time.
        _text(encoded_flag),
        POP,
        # 2) Code execution: builtins.print(warning); discard its result (None).
        GLOBAL + b"builtins\nprint\n",
        _text(warning),
        TUPLE1,
        REDUCE,
        POP,
        # 3) The "model": builtins.dict([("model", "fake"), ("version", 1)]).
        _short("builtins"),
        _short("dict"),
        STACK_GLOBAL,
        EMPTY_LIST,
        MARK,
        _short("model") + _short("fake") + TUPLE2,
        _short("version") + BININT1 + b"\x01" + TUPLE2,
        APPENDS,
        TUPLE1,
        REDUCE,
        STOP,
    ]
    return b"".join(parts)


def generate(ctx: GenerationContext) -> None:
    warning = ctx.asset_text("warning.txt").strip()
    payload = build_pickle(ctx.flag, warning)
    (ctx.workspace / "sentiment_model.pkl").write_bytes(payload)
