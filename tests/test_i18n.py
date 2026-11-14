"""i18n infrastructure: catalogue completeness, fallback and "no embedded text"."""

from __future__ import annotations

import ast
import importlib.util
import re
import shutil
from pathlib import Path

import pytest
import yaml
from helpers import REPO_ROOT, hash_tree, invoke

from tensorgoat.core import i18n
from tensorgoat.core.scenario import DIFFICULTIES, TYPES
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

PACKAGE = REPO_ROOT / "tensorgoat"
EN = i18n.load_yaml(PACKAGE / "locales" / "en.yml")
LITERAL_OK = "i18n: literal-ok"


# ------------------------------------------------------------ language choice
def test_default_language_is_english_and_system_locale_is_ignored():
    environ = {"LANG": "tr_TR.UTF-8", "LC_ALL": "tr_TR.UTF-8"}
    assert i18n.resolve_language(environ=environ) == "en"


def test_language_priority():
    env = {"TENSORGOAT_LANG": "de"}
    assert i18n.resolve_language("tr", "fr", env) == "tr"
    assert i18n.resolve_language(None, "fr", env) == "de"
    assert i18n.resolve_language(None, "fr", {}) == "fr"
    assert i18n.resolve_language(None, None, {}) == "en"
    assert i18n.resolve_language(" TR ", None, {}) == "tr"


def test_available_languages_are_discovered_from_files(tmp_path):
    for code in ("tr", "en", "de"):
        (tmp_path / f"{code}.yml").write_text("app: {}\n", encoding="utf-8")
    assert i18n.available_languages(tmp_path) == ["en", "de", "tr"]
    assert i18n.available_languages() == sorted(
        (p.stem for p in (PACKAGE / "locales").glob("*.yml")), key=lambda c: (c != "en", c)
    )


def test_accept_language_negotiation():
    available = ["en", "tr"]
    assert i18n.negotiate_language("tr-TR,tr;q=0.9,en;q=0.8", available, "en") == "tr"
    assert i18n.negotiate_language("de;q=0.9, tr;q=0.5", available, "en") == "tr"
    assert i18n.negotiate_language("en;q=0.2, tr;q=0.9", available, "en") == "tr"
    assert i18n.negotiate_language("de, fr", available, "tr") == "tr"
    assert i18n.negotiate_language(None, available, "en") == "en"
    assert i18n.negotiate_language("*", available, "en") == "en"


# --------------------------------------------------------------- completeness
def _catalogue_keys_used_in(source: str) -> set[str]:
    pattern = (
        r"""(?:_h|\.t|\.text|_say|_fail)\(\s*(?:session,\s*)?["']([a-z_]+(?:\.[a-z_\-]+)+)["']"""
    )
    keys = set(re.findall(pattern, source))
    keys |= set(re.findall(r"""RunnerError\(\s*["']([a-z_]+\.[a-z_]+)["']""", source))
    keys |= set(re.findall(r"""["'](create\.[a-z_]+)["']""", source))
    keys |= set(re.findall(r"""notify\(\s*["']([a-z_]+\.[a-z_]+)["']""", source))
    return keys


def test_english_catalogue_has_every_key_the_code_uses():
    used: set[str] = set()
    for path in (PACKAGE / "cli.py", PACKAGE / "core" / "runner.py", PACKAGE / "core" / "ops.py"):
        used |= _catalogue_keys_used_in(path.read_text(encoding="utf-8"))
    used |= {f"difficulty.{name}" for name in DIFFICULTIES}
    used |= {f"type.{name}" for name in TYPES}
    used |= {f"status.{c}" for c in ("col_id", "col_mode", "col_url", "col_pid", "col_state")}
    assert len(used) > 40, "key extraction looks broken"
    missing = sorted(key for key in used if not isinstance(i18n.lookup(EN, key), str))
    assert not missing, f"keys missing from locales/en.yml: {missing}"


def test_english_catalogue_has_no_empty_values():
    empty = [key for key, value in i18n.flatten(EN).items() if not str(value).strip()]
    assert not empty


@pytest.mark.parametrize("scenario", all_scenarios(), ids=lambda s: s.id)
def test_english_scenario_files_are_complete(scenario):
    assert (scenario.path / "BRIEFING.en.md").read_text(encoding="utf-8").strip()
    texts = i18n.load_yaml(scenario.path / "i18n.en.yml")
    assert str(texts.get("title", "")).strip()
    assert str(texts.get("summary", "")).strip()
    assert texts.get("learning_objectives"), "at least one learning objective"
    assert isinstance(texts.get("messages"), dict)
    hints, _ = i18n.load_hints(scenario.path, "en")
    assert len(hints) == 3 and all(hint.strip() for hint in hints)
    raw_hints = i18n.load_yaml(scenario.path / "hints.en.yml")["hints"]
    assert [entry["level"] for entry in raw_hints] == [1, 2, 3]

    if scenario.is_service:
        source = (scenario.path / "service.py").read_text(encoding="utf-8")
        used = set(re.findall(r"""\.message\(\s*["']([a-z_]+)["']""", source))
        assert used, "a service must take its messages from the catalogue"
        shared = EN.get("service", {})
        missing = sorted(key for key in used if key not in texts["messages"] and key not in shared)
        assert not missing, f"{scenario.id}: messages missing from i18n.en.yml: {missing}"


@pytest.mark.parametrize("scenario", all_scenarios(), ids=lambda s: s.id)
def test_hint_tiers_match_english_in_every_language(scenario):
    english = [e["level"] for e in i18n.load_yaml(scenario.path / "hints.en.yml")["hints"]]
    for path in scenario.path.glob("hints.*.yml"):
        levels = [entry["level"] for entry in i18n.load_yaml(path)["hints"]]
        assert levels == english, f"{path.name} must have the same tiers in the same order"


# ------------------------------------------------- no hard-coded player texts
def _literal_prints(path: Path) -> list[int]:
    """Lines where ``print(...)`` / ``x.print(...)`` receives a string literal."""
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    offenders: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "print":
            continue
        first = node.args[0]
        is_literal = isinstance(first, ast.JoinedStr) or (
            isinstance(first, ast.Constant) and isinstance(first.value, str)
        )
        if is_literal and LITERAL_OK not in lines[node.lineno - 1]:
            offenders.append(node.lineno)
    return offenders


def test_static_check_detects_literals(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text(
        "print('hello')\n"
        "console.print(f'hi {name}')\n"
        "console.print(text)\n"
        "print('ok')  # i18n: literal-ok\n",
        encoding="utf-8",
    )
    assert _literal_prints(sample) == [1, 2]


def test_no_hardcoded_player_text_in_cli_and_services():
    files = [PACKAGE / "cli.py", *sorted((PACKAGE / "scenarios").glob("*/service.py"))]
    offenders = {
        path.relative_to(REPO_ROOT).as_posix(): lines
        for path in files
        if (lines := _literal_prints(path))
    }
    assert not offenders, f"string literals passed to print(): {offenders}"


def test_services_keep_machine_fields_out_of_translations():
    """Services must not put literal sentences into JSON; texts come via .message()."""
    for path in sorted((PACKAGE / "scenarios").glob("*/service.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if isinstance(key, ast.Constant) and key.value == "message":
                        assert not isinstance(value, ast.Constant | ast.JoinedStr), (
                            f"{path.name}:{node.lineno} has a hard-coded message"
                        )


# -------------------------------------------------------------------- fallback
@pytest.fixture
def fake_locales(tmp_path, monkeypatch) -> Path:
    """A locales directory with English plus an incomplete fake language ``xx``."""
    locales = tmp_path / "locales"
    locales.mkdir()
    shutil.copy(PACKAGE / "locales" / "en.yml", locales / "en.yml")
    partial = {"list": {"title": "XX SCENARIOS XX"}, "lang": {"active": "XX ACTIVE {lang}"}}
    (locales / "xx.yml").write_text(yaml.safe_dump(partial), encoding="utf-8")
    monkeypatch.setattr(i18n, "LOCALES_DIR", locales)
    return locales


def test_translator_uses_language_then_falls_back_to_english(fake_locales):
    translator = i18n.Translator("xx")
    assert translator.t("list.title") == "XX SCENARIOS XX"
    assert translator.fallback_used is False
    assert translator.t("list.col_id") == i18n.lookup(EN, "list.col_id")
    assert translator.fallback_used is True
    assert i18n.available_languages() == ["en", "xx"]


def test_english_never_reports_fallback():
    translator = i18n.Translator("en")
    translator.t("list.title")
    translator.scenario_texts(get_scenario("first_flag").path)
    translator.hints(get_scenario("first_flag").path)
    translator.file_text(get_scenario("first_flag").path, "BRIEFING", "md")
    assert translator.fallback_used is False


def test_broken_placeholder_does_not_crash(fake_locales):
    (fake_locales / "xx.yml").write_text("lang:\n  active: 'XX {wrong_name}'\n", encoding="utf-8")
    assert i18n.Translator("xx").t("lang.active", lang="xx") == "XX {wrong_name}"


def test_scenario_texts_fall_back_per_file_and_per_key(tmp_path):
    source = get_scenario("first_flag").path
    folder = tmp_path / source.name
    shutil.copytree(source, folder)
    (folder / "i18n.xx.yml").write_text("title: 'XX TITLE'\n", encoding="utf-8")
    hints = {"hints": [{"level": 1, "text": "XX HINT ONE"}]}
    (folder / "hints.xx.yml").write_text(yaml.safe_dump(hints), encoding="utf-8")

    translator = i18n.Translator("xx")
    texts = translator.scenario_texts(folder)
    english = i18n.load_yaml(source / "i18n.en.yml")
    assert texts["title"] == "XX TITLE"
    assert texts["learning_objectives"] == english["learning_objectives"]
    assert translator.fallback_used

    english_hints, _ = i18n.load_hints(source, "en")
    assert translator.hints(folder) == ["XX HINT ONE", *english_hints[1:]]
    assert translator.file_text(folder, "BRIEFING", "md") == (
        (source / "BRIEFING.en.md").read_text(encoding="utf-8")
    )

    (folder / "BRIEFING.xx.md").write_text("XX BRIEFING", encoding="utf-8")
    assert i18n.Translator("xx").file_text(folder, "BRIEFING", "md") == "XX BRIEFING"


def test_cli_falls_back_and_prints_one_note(fake_locales):
    result = invoke("--lang", "xx", "list")
    assert result.exit_code == 0, result.output
    assert "XX SCENARIOS XX" in result.output
    assert i18n.lookup(EN, "list.col_difficulty") in result.output
    note = i18n.lookup(EN, "app.fallback_note").format(lang="xx")
    assert result.output.count(note) == 1

    english = invoke("list")
    assert note not in english.output


def test_cli_language_sources(fake_locales, monkeypatch, state: State):
    assert "XX ACTIVE xx" in invoke("--lang", "xx", "lang").output
    monkeypatch.setenv("TENSORGOAT_LANG", "xx")
    assert "XX ACTIVE xx" in invoke("lang").output
    monkeypatch.delenv("TENSORGOAT_LANG")
    assert invoke("lang", "xx").exit_code == 0
    assert state.get_lang() == "xx"
    assert "XX ACTIVE xx" in invoke("lang").output
    assert "XX ACTIVE" not in invoke("--lang", "en", "lang").output


def test_flags_do_not_depend_on_language(fake_locales, monkeypatch, isolated_home):
    scenario = get_scenario("first_flag")
    state = State(isolated_home)
    assert invoke("create", scenario.id).exit_code == 0
    english_files = hash_tree(state.workspace_dir(scenario.id))
    english_flag = scenario.flag(state)

    monkeypatch.setenv("TENSORGOAT_LANG", "xx")
    assert invoke("create", scenario.id).exit_code == 0
    assert hash_tree(state.workspace_dir(scenario.id)) == english_files
    assert scenario.flag(State(isolated_home)) == english_flag
    assert invoke("submit", scenario.id, english_flag).exit_code == 0


# ---------------------------------------------------------------------- report
def _load_report_module():
    script = REPO_ROOT / "scripts" / "i18n_report.py"
    spec = importlib.util.spec_from_file_location("i18n_report", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_i18n_report_english_is_complete_and_missing_language_is_reported(capsys):
    report = _load_report_module()
    assert report.is_complete(report.build_report("en")), report.render(
        "en", report.build_report("en")
    )
    missing = report.build_report("xx")
    assert "tensorgoat/locales/xx.yml" in missing["missing_files"]
    assert any(path.endswith("BRIEFING.xx.md") for path in missing["missing_files"])
    assert report.main(["--lang", "xx"]) == 0, "the report is informational"
    assert report.main(["--lang", "xx", "--strict"]) == 1
    assert "missing file" in capsys.readouterr().out


def test_i18n_report_lists_missing_keys(fake_locales):
    report = _load_report_module()
    result = report.build_report("xx", locales_dir=fake_locales)
    (keys,) = [v for k, v in result["missing_keys"].items() if k.endswith("xx.yml")]
    assert "list.col_id" in keys and "list.title" not in keys
