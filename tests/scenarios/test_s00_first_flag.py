from __future__ import annotations

import re
import time

from helpers import assert_deterministic, assert_small_artifacts, assert_solvable

from tensorgoat.core.state import State

SID = "s00_first_flag"


def test_generate_deterministic(tmp_path):
    assert_deterministic(SID, tmp_path)


def test_solve(isolated_home):
    assert_solvable(SID, isolated_home)


def test_unintended_flag_is_only_inside_the_html_comment(generated):
    scenario, state, ctx = generated(SID)
    raw = (ctx.workspace / "model_card.md").read_text(encoding="utf-8")
    assert raw.count(ctx.flag) == 1
    rendered = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    assert ctx.flag not in rendered and "TGOAT" not in rendered


def test_resource_budget(tmp_path):
    from tensorgoat.scenarios import get_scenario

    state = State(tmp_path / "home")
    started = time.monotonic()
    get_scenario(SID).generate(state)
    assert time.monotonic() - started < 60
    assert_small_artifacts(SID, state)
