"""Every install must be solvable, not just the one with the CI seed.

Each seed stands for a different install secret, i.e. different data, models
and flags. For every seed all scenarios are generated and solved with the
public solvers (service scenarios in-process, without starting a server).

The default sweep is small to keep the suite fast. Widen it with, for example,
``TENSORGOAT_SWEEP_SEEDS=30 pytest tests/test_seed_sweep.py``.
"""

from __future__ import annotations

import importlib.util
import os

import httpx
import pytest
from fastapi.testclient import TestClient
from helpers import SOLUTIONS

from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios

SEED_COUNT = int(os.environ.get("TENSORGOAT_SWEEP_SEEDS", "3"))
SEEDS = [f"sweep-{index}" for index in range(SEED_COUNT)]


def _load_solver(scenario_id: str):
    path = SOLUTIONS / scenario_id / "solve.py"
    spec = importlib.util.spec_from_file_location(f"solve_{scenario_id}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("seed", SEEDS)
def test_every_scenario_is_solvable_for_this_install(seed, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TENSORGOAT_SEED", seed)
    state = State(tmp_path / "home")
    flags_seen = set()
    for scenario in all_scenarios():
        scenario.generate(state)
        workspace = state.workspace_dir(scenario.id)
        solver = _load_solver(scenario.id)
        if scenario.is_service:
            app = scenario.create_app(state)
            # The solvers build an httpx.Client; hand them an in-process one instead.
            monkeypatch.setattr(httpx, "Client", lambda app=app, **_: TestClient(app))
            takes_workspace = "workspace" in solver.solve.__code__.co_varnames[:2]
            url = "http://testserver"
            flag = solver.solve(workspace, url) if takes_workspace else solver.solve(url)
        else:
            flag = solver.solve(workspace)
        assert flag == scenario.flag(state), f"{scenario.id} with seed {seed!r}"
        flags_seen.add(flag)
    assert len(flags_seen) == len(all_scenarios())
    capsys.readouterr()  # drop the solvers' progress output


def test_different_installs_get_different_flags_and_data(tmp_path, monkeypatch):
    from helpers import hash_tree

    results = []
    for seed in ("install-a", "install-b"):
        monkeypatch.setenv("TENSORGOAT_SEED", seed)
        state = State(tmp_path / seed)
        scenario = next(s for s in all_scenarios() if s.id == "s04_trojan_filter")
        scenario.generate(state)
        results.append((scenario.flag(state), hash_tree(state.workspace_dir(scenario.id))))
    assert results[0][0] != results[1][0]
    assert results[0][1] != results[1][1]
