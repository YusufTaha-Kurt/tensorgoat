"""Shared fixtures: a deterministic seed and an isolated state directory per test."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# CI sets TENSORGOAT_SEED=ci; locally any fixed value gives deterministic flags.
SEED = os.environ.setdefault("TENSORGOAT_SEED", "pytest")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tensorgoat.core.state import State  # noqa: E402
from tensorgoat.scenarios import get_scenario  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch) -> Path:
    """Every test gets its own TENSORGOAT_HOME and a clean language setting."""
    home = tmp_path / "tgoat-home"
    monkeypatch.setenv("TENSORGOAT_HOME", str(home))
    monkeypatch.setenv("TENSORGOAT_SEED", SEED)
    monkeypatch.delenv("TENSORGOAT_LANG", raising=False)
    monkeypatch.setenv("COLUMNS", "200")  # keep rich tables and panels unwrapped
    return home


@pytest.fixture
def state(isolated_home) -> State:
    return State(isolated_home)


@pytest.fixture(scope="session")
def generated(tmp_path_factory):
    """Generate a scenario once per test session: ``generated("s03_model_heist")``.

    Returns ``(scenario, state, ctx)``. Tests must treat the files as read-only.
    """
    home = tmp_path_factory.mktemp("session-home")
    cache: dict[str, tuple] = {}

    def _generate(scenario_id: str):
        if scenario_id not in cache:
            session_state = State(home)
            scenario = get_scenario(scenario_id)
            cache[scenario_id] = (scenario, session_state, scenario.generate(session_state))
        return cache[scenario_id]

    return _generate
