"""The translations that ship with the project (Turkish) are complete and consistent."""

from __future__ import annotations

import importlib.util
import re

import pytest
import yaml
from helpers import REPO_ROOT, SOLUTIONS, invoke

from tensorgoat.core import i18n
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

PACKAGE = REPO_ROOT / "tensorgoat"
SCENARIOS = all_scenarios()
by_id = pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.id)
TRANSLATIONS = [lang for lang in i18n.available_languages() if lang != "en"]

DOCUMENTS = ("ARCHITECTURE", "DECISIONS", "ROADMAP", "SCENARIO_AUTHORING", "TRANSLATING")
ROOT_DOCUMENTS = ("CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "DISCLAIMER.md")
SYNTHETIC_DATA = {
    "s00_first_flag",
    "s03_model_heist",
    "s04_trojan_filter",
    "s05_whos_in_the_data",
    "s06_ghost_badge",
}
TURKISH_SECTIONS = (
    "## Senaryo özeti",
    "## Keşif",
    "## Saldırı",
    "## Neden işe yarıyor",
    "## Önlem / Savunma",
    "## Gerçek dünyadan kaynaklar",
)


def _report_module():
    script = REPO_ROOT / "scripts" / "i18n_report.py"
    spec = importlib.util.spec_from_file_location("i18n_report", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _placeholders(text: str) -> set[str]:
    """``{name}`` placeholders of a catalogue text; doubled braces are literals."""
    return set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", str(text)))


def _markup(text: str) -> list[str]:
    return sorted(re.findall(r"\[/?[a-z ]+\]", str(text)))


def _catalogue_pairs(lang: str):
    """Yield ``(file, key, english, translated)`` for every translated catalogue text."""
    pairs = [(PACKAGE / "locales" / "en.yml", PACKAGE / "locales" / f"{lang}.yml")]
    for scenario in SCENARIOS:
        pairs.append((scenario.path / "i18n.en.yml", scenario.path / f"i18n.{lang}.yml"))
    for english_path, local_path in pairs:
        english = i18n.flatten(i18n.load_yaml(english_path))
        local = i18n.flatten(i18n.load_yaml(local_path))
        for key, value in english.items():
            if key in local and isinstance(value, str):
                yield local_path.name, key, value, local[key]


def _links(text: str) -> set[str]:
    return set(re.findall(r"https?://[^\s<>)\]]+", text))


# ------------------------------------------------------------------ catalogues
def test_turkish_ships_with_the_project():
    assert "tr" in TRANSLATIONS


@pytest.mark.parametrize("lang", TRANSLATIONS)
def test_translation_is_complete(lang):
    report = _report_module()
    result = report.build_report(lang)
    assert report.is_complete(result) and not result["notes"], report.render(lang, result)


@pytest.mark.parametrize("lang", TRANSLATIONS)
def test_translation_keeps_placeholders_and_markup(lang):
    problems = []
    for file_name, key, english, translated in _catalogue_pairs(lang):
        if _placeholders(english) != _placeholders(translated):
            problems.append(f"{file_name}:{key} placeholders differ")
        if _markup(english) != _markup(translated):
            problems.append(f"{file_name}:{key} markup differs")
        if "TGOAT{{" in english and "TGOAT{{" not in translated:
            problems.append(f"{file_name}:{key} lost the flag format")
    assert not problems, problems


@pytest.mark.parametrize("lang", TRANSLATIONS)
def test_translation_does_not_translate_commands(lang):
    """Commands inside a text must stay exactly as the player has to type them."""
    command = re.compile(r"tensorgoat [a-z]+(?: [a-z_]+)?")
    problems = []
    for file_name, key, english, translated in _catalogue_pairs(lang):
        for found in command.findall(english):
            verb = " ".join(found.split()[:2])
            if verb not in translated:
                problems.append(f"{file_name}:{key} lost '{verb}'")
    assert not problems, problems


@pytest.mark.parametrize("lang", TRANSLATIONS)
def test_translated_cli_runs_without_falling_back(lang, state: State):
    note = i18n.Translator(lang).t("app.fallback_note", lang=lang)
    for command in (["list"], ["briefing", "s06"], ["status"], ["lang"], ["--help"]):
        result = invoke("--lang", lang, *command)
        assert result.exit_code == 0, result.output
        assert note not in result.output, command
    scenario = get_scenario("first_flag")
    created = invoke("--lang", lang, "create", "first_flag")
    assert created.exit_code == 0 and note not in created.output
    title = i18n.load_yaml(scenario.path / f"i18n.{lang}.yml")["title"]
    assert title in created.output
    hint = invoke("--lang", lang, "hint", "first_flag")
    local_hints, fell_back = i18n.load_hints(scenario.path, lang)
    assert not fell_back and local_hints[0][:40] in hint.output
    assert invoke("--lang", lang, "submit", "first_flag", scenario.flag(state)).exit_code == 0
    shown = invoke("--lang", lang, "walkthrough", "first_flag")
    assert shown.exit_code == 0 and note not in shown.output


@by_id
def test_translated_service_speaks_the_language(scenario, generated):
    """A service started in Turkish answers in Turkish, with unchanged machine fields."""
    if not scenario.is_service:
        pytest.skip("artifact scenario")
    from fastapi.testclient import TestClient

    _, state, _ = generated(scenario.id)
    english = TestClient(scenario.create_app(state, default_lang="en")).get("/").json()
    turkish = TestClient(scenario.create_app(state, default_lang="tr")).get("/").json()
    assert turkish["message"] != english["message"]
    assert (
        turkish["message"]
        == i18n.load_yaml(scenario.path / "i18n.tr.yml")["messages"]["description"]
    )
    english.pop("message"), turkish.pop("message")
    assert turkish == english, "only the message may depend on the language"


# ------------------------------------------------------------------- scenarios
@by_id
def test_translated_walkthroughs_keep_the_structure(scenario):
    folder = SOLUTIONS / scenario.id
    english = (folder / "WALKTHROUGH.en.md").read_text(encoding="utf-8")
    translated = [path for path in folder.glob("WALKTHROUGH.*.md") if ".en." not in path.name]
    assert translated, "at least the Turkish walkthrough is expected"
    for path in translated:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("# ") and text.splitlines()[2].startswith("> ⚠️"), path.name
        assert text.count("\n## ") == english.count("\n## "), f"{path.name}: sections differ"
        assert text.count("```") == english.count("```"), f"{path.name}: code blocks differ"
        assert _links(text) == _links(english), f"{path.name}: references differ"
    turkish = (folder / "WALKTHROUGH.tr.md").read_text(encoding="utf-8")
    positions = [turkish.find(section) for section in TURKISH_SECTIONS]
    assert all(position >= 0 for position in positions) and positions == sorted(positions)
    defence = turkish.split("## Önlem / Savunma")[1].split("## Gerçek dünyadan kaynaklar")[0]
    assert len(defence.split()) > 80, "the defence section must be substantial"


@by_id
def test_translated_briefings_have_no_spoilers_and_declare_synthetic_data(scenario):
    for path in scenario.path.glob("BRIEFING.*.md"):
        briefing = path.read_text(encoding="utf-8")
        assert "TGOAT{" not in briefing.replace("TGOAT{...}", ""), path.name
        assert "solve.py" not in briefing and "WALKTHROUGH" not in briefing, path.name
    if scenario.id in SYNTHETIC_DATA:
        turkish = (scenario.path / "BRIEFING.tr.md").read_text(encoding="utf-8")
        assert "sentetik" in turkish.lower(), "the briefing must say the data is synthetic"


@by_id
def test_translated_briefings_keep_the_technical_details(scenario):
    """Every `code` span of the English briefing appears in the translation too."""
    english = (scenario.path / "BRIEFING.en.md").read_text(encoding="utf-8")
    for path in scenario.path.glob("BRIEFING.*.md"):
        text = " ".join(path.read_text(encoding="utf-8").split())
        for span in re.findall(r"`([^`\n]+)`", english):
            if re.search(r"[a-z]{3,} [a-z]{3,} [a-z]{3,}", span.split("{")[0]):
                continue  # a span that contains a translatable phrase
            if span in ("python model.py",) or "[" in span:
                continue  # spans whose inner description is translated
            assert span in text, f"{path.name} lost `{span}`"


# ------------------------------------------------------------------- documents
def test_turkish_documentation_mirrors_the_english_one():
    readme = (REPO_ROOT / "README.tr.md").read_text(encoding="utf-8")
    solutions_readme = (SOLUTIONS / "README.tr.md").read_text(encoding="utf-8")
    for scenario in SCENARIOS:
        title = yaml.safe_load((scenario.path / "i18n.tr.yml").read_text(encoding="utf-8"))["title"]
        assert f"`{scenario.id}`" in readme, f"{scenario.id} is missing from README.tr.md"
        assert title in readme
        assert f"{scenario.id}/WALKTHROUGH.tr.md" in solutions_readme
    documents = [REPO_ROOT / "docs" / f"{name}.md" for name in DOCUMENTS]
    documents += [REPO_ROOT / name for name in ROOT_DOCUMENTS]
    documents += [REPO_ROOT / "README.md", SOLUTIONS / "README.md"]
    for english in documents:
        turkish = english.with_suffix(".tr.md")
        assert turkish.is_file(), f"{turkish.name} is missing"
        # Each version links to the other one.
        assert turkish.name in english.read_text(encoding="utf-8"), english.name
        assert english.name in turkish.read_text(encoding="utf-8"), turkish.name
    assert (REPO_ROOT / "docs" / "tr" / "sozluk.md").is_file()


def test_links_between_documents_resolve():
    """Relative links in the documentation must point at existing files."""
    documents = [*REPO_ROOT.glob("*.md"), *(REPO_ROOT / "docs").rglob("*.md")]
    documents += [*SOLUTIONS.glob("*.md")]
    assert len(documents) > 20
    broken = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        targets = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text)
        targets += re.findall(r'(?:href|src)="([^"#]+)"', text)
        for target in targets:
            if re.match(r"[a-z]+:", target):
                continue
            if not (document.parent / target).exists():
                broken.append(f"{document.relative_to(REPO_ROOT).as_posix()} -> {target}")
    assert not broken, broken
