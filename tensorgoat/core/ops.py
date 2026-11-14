"""Scenario operations shared by the command line and the local web interface.

Both front ends do the same things to a scenario (create, destroy, open a hint,
check a flag, find the walkthrough). The logic lives here once; the front ends
only decide how to show the result.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tensorgoat.core import flags, i18n, runner
from tensorgoat.core.scenario import Scenario
from tensorgoat.core.state import State

PACKAGE_DIR = Path(__file__).resolve().parent.parent
WALKTHROUGH = "WALKTHROUGH"


def remove_files(state: State, scenario_id: str) -> None:
    """Delete workspace and internals; retry while a stopping service holds files."""
    for _ in range(25):
        state.remove_scenario_files(scenario_id)
        if not state.workspace_dir(scenario_id).exists() and not (
            state.internal_dir(scenario_id).exists()
        ):
            return
        time.sleep(0.2)


def create(
    state: State,
    scenario: Scenario,
    *,
    lang: str,
    port: int | None = None,
    docker: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Generate the artefacts and (re)start the service. Returns the new record.

    ``progress`` receives the catalogue key of each step as it begins. Raises
    :class:`runner.RunnerError` when the service cannot be started.
    """
    notify = progress or (lambda key: None)
    previous = state.record(scenario.id)
    if scenario.is_service and previous["created"]:
        # Creating again restarts the service (and resets its counters).
        runner.stop(state, scenario, previous)

    notify("create.generating")
    scenario.generate(state)
    record = state.update_record(scenario.id, created=True, mode=None, port=None, pid=None)

    if scenario.is_service:
        chosen_port = port or int(scenario.port or 0)
        notify("create.starting_service")
        pid = runner.start(state, scenario, port=chosen_port, lang=lang, docker=docker)
        record = state.update_record(
            scenario.id, mode="docker" if docker else "native", port=chosen_port, pid=pid
        )
    return record


def destroy(state: State, scenario: Scenario) -> None:
    """Stop the service and delete the scenario's files; progress is kept."""
    runner.stop(state, scenario, state.record(scenario.id))
    remove_files(state, scenario.id)
    state.update_record(scenario.id, created=False, mode=None, port=None, pid=None)


def submit(state: State, scenario: Scenario, flag: str) -> tuple[bool, bool]:
    """Check a flag. Returns ``(correct, was_already_solved)``."""
    if not flags.verify_flag(state.install_secret(), scenario.id, scenario.slug, flag):
        return False, bool(state.record(scenario.id)["solved"])
    already = bool(state.record(scenario.id)["solved"])
    state.update_record(scenario.id, solved=True)
    return True, already


def solutions_dir() -> Path | None:
    """Where the walkthroughs live: inside an installed package, or in a checkout."""
    for candidate in (PACKAGE_DIR / "_solutions", PACKAGE_DIR.parent / "solutions"):
        if candidate.is_dir():
            return candidate
    return None


def walkthrough_path(scenario: Scenario, lang: str) -> tuple[Path | None, bool]:
    """``(path, fell_back_to_english)`` of a scenario's walkthrough, if it is installed."""
    root = solutions_dir()
    if root is None:
        return None, False
    path, fell_back = i18n.localized_path(root / scenario.id, WALKTHROUGH, "md", lang)
    return (path, fell_back) if path.is_file() else (None, False)
