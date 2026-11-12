"""Scenario registry: every sub-folder with a ``scenario.yml`` is a scenario."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tensorgoat.core.scenario import Registry, Scenario

SCENARIOS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def registry() -> Registry:
    return Registry(SCENARIOS_DIR)


def all_scenarios() -> list[Scenario]:
    return registry().all()


def get_scenario(name: str) -> Scenario:
    return registry().get(name)
