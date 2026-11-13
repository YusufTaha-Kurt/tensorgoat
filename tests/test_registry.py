"""Every scenario folder is complete and follows the scenario.yml schema."""

from __future__ import annotations

import ast
import inspect
import re

import pytest
import yaml
from helpers import REPO_ROOT, SOLUTIONS

from tensorgoat.core.scenario import (
    REQUIRED_FILES,
    SERVICE_FILES,
    Registry,
    ScenarioNotFound,
    validate_meta,
)
from tensorgoat.scenarios import SCENARIOS_DIR, all_scenarios, get_scenario

ALLOWED_KEYS = {
    "id",
    "slug",
    "difficulty",
    "type",
    "estimated_time_minutes",
    "port",
    "categories",
    "tools_suggested",
    "tunable_params",
}
WALKTHROUGH_SECTIONS = (
    "## Scenario recap",
    "## Recon",
    "## Exploitation",
    "## Why this works",
    "## Mitigation / Defense",
    "## Real-world references",
)
# Scenarios whose artefacts or services contain synthetic records about "people"
# or organisations: their briefing must say so explicitly (design principle 7).
SYNTHETIC_DATA = {"s00_first_flag", "s03_model_heist", "s04_trojan_filter", "s05_whos_in_the_data"}
SOLVER_DEPENDENCIES = {"numpy", "sklearn", "safetensors", "httpx"}

SCENARIOS = all_scenarios()
by_id = pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)


def test_scenarios_are_discovered_in_order():
    ids = [scenario.id for scenario in SCENARIOS]
    assert len(ids) >= 7
    assert ids == sorted(ids)
    assert ids[0] == "s00_first_flag"
    assert len({scenario.slug for scenario in SCENARIOS}) == len(ids)
    ports = [scenario.port for scenario in SCENARIOS if scenario.is_service]
    assert len(set(ports)) == len(ports), "every service needs its own port"


def test_no_half_added_scenario_folders():
    folders = {p.name for p in SCENARIOS_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert folders == {scenario.id for scenario in SCENARIOS}
    solved = {p.name for p in SOLUTIONS.iterdir() if p.is_dir()}
    assert solved == folders, "solutions/ and scenarios/ must list the same scenarios"


@by_id
def test_required_files_exist(scenario):
    for name in REQUIRED_FILES:
        assert (scenario.path / name).is_file(), f"{scenario.id} is missing {name}"
    if scenario.is_service:
        for name in SERVICE_FILES:
            assert (scenario.path / name).is_file(), f"{scenario.id} is missing {name}"
    else:
        assert not (scenario.path / "service.py").exists()
    assert (SOLUTIONS / scenario.id / "solve.py").is_file()
    assert (SOLUTIONS / scenario.id / "WALKTHROUGH.en.md").is_file()


@by_id
def test_scenario_yml_matches_schema(scenario):
    meta = yaml.safe_load((scenario.path / "scenario.yml").read_text(encoding="utf-8"))
    assert validate_meta(meta, folder_name=scenario.path.name) == []
    assert set(meta) <= ALLOWED_KEYS, f"unknown keys: {set(meta) - ALLOWED_KEYS}"
    assert set(meta) >= ALLOWED_KEYS - {"tunable_params"}
    # Player-facing text lives in i18n.<lang>.yml, never in scenario.yml.
    assert "title" not in meta and "learning_objectives" not in meta
    for category in meta["categories"]:
        assert not re.search(r"AML\.T\d+", category), "use ATLAS technique names, not ids"


@by_id
def test_modules_expose_the_expected_entry_points(scenario):
    generate = scenario._module("generate").generate
    assert list(inspect.signature(generate).parameters) == ["ctx"]
    if scenario.is_service:
        create_app = scenario._module("service").create_app
        parameters = list(inspect.signature(create_app).parameters)
        assert parameters[:3] == ["flag_provider", "params", "default_lang"]


@by_id
def test_walkthrough_follows_the_template(scenario):
    text = (SOLUTIONS / scenario.id / "WALKTHROUGH.en.md").read_text(encoding="utf-8")
    assert text.startswith("# ") and "SPOILER" in text.splitlines()[2]
    positions = [text.find(section) for section in WALKTHROUGH_SECTIONS]
    assert all(position >= 0 for position in positions), "a template section is missing"
    assert positions == sorted(positions), "sections are out of order"
    defence = text.split("## Mitigation / Defense")[1].split("## Real-world references")[0]
    assert len(defence.split()) > 80, "the defence section must be substantial"


@by_id
def test_solver_only_uses_player_resources(scenario):
    """solve.py may use the workspace and the service, never TensorGoat internals."""
    source = (SOLUTIONS / scenario.id / "solve.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    third_party = {name for name in imported if name not in sys_stdlib()}
    assert third_party <= SOLVER_DEPENDENCIES, f"unexpected imports: {third_party}"
    for forbidden in ("tensorgoat", "config.yml", "state.json", "install_secret", "params.json"):
        assert forbidden not in source.replace("TensorGoat", ""), forbidden
    assert "--workspace" in source and "--url" in source
    assert '"message"]' not in source and "['message']" not in source, "read error_code instead"


def sys_stdlib() -> set[str]:
    import sys

    return set(sys.stdlib_module_names) | {"__future__"}


@by_id
def test_briefing_has_no_spoilers_and_declares_synthetic_data(scenario):
    briefing = (scenario.path / "BRIEFING.en.md").read_text(encoding="utf-8")
    assert "TGOAT{" not in briefing.replace("TGOAT{...}", "")
    assert "solve.py" not in briefing and "WALKTHROUGH" not in briefing
    if scenario.id in SYNTHETIC_DATA:
        assert "synthetic" in briefing.lower(), "the briefing must say the data is synthetic"


def test_lookup_by_id_slug_and_prefix():
    assert get_scenario("s02_pickle_jar").slug == "pickle_jar"
    assert get_scenario("pickle_jar").id == "s02_pickle_jar"
    assert get_scenario("Pickle-Jar").id == "s02_pickle_jar"
    assert get_scenario("s02").id == "s02_pickle_jar"
    with pytest.raises(ScenarioNotFound):
        get_scenario("nope")


def test_validate_meta_reports_problems():
    good = {
        "id": "s09_example",
        "slug": "example",
        "difficulty": "easy",
        "type": "service",
        "estimated_time_minutes": 10,
        "port": 8199,
        "categories": ["Example"],
        "tools_suggested": [],
        "tunable_params": {},
    }
    assert validate_meta(good, folder_name="s09_example") == []
    assert validate_meta(good, folder_name="s10_other")
    for key, bad in (
        ("id", "example"),
        ("slug", "Other"),
        ("difficulty", "hard"),
        ("type", "web"),
        ("estimated_time_minutes", 0),
        ("port", None),
        ("port", 80),
        ("categories", []),
        ("categories", "one string"),
        ("tunable_params", [1, 2]),
    ):
        assert validate_meta({**good, key: bad}), f"{key}={bad!r} must be rejected"
    artifact = {**good, "type": "artifact"}
    assert validate_meta(artifact), "artifact scenarios must not declare a port"
    assert validate_meta({**artifact, "port": None}) == []


def test_registry_rejects_an_invalid_scenario(tmp_path):
    folder = tmp_path / "s01_broken"
    folder.mkdir()
    (folder / "scenario.yml").write_text("id: s01_broken\nslug: broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="s01_broken"):
        Registry(tmp_path).all()


def test_repository_layout():
    for name in ("README.md", "LICENSE", "pyproject.toml", ".gitignore"):
        assert (REPO_ROOT / name).is_file(), name
