#!/usr/bin/env python3
"""Report which translated files and keys are missing, per language.

Usage:
    python scripts/i18n_report.py            # all languages found in tensorgoat/locales
    python scripts/i18n_report.py --lang tr  # one language (it may not exist yet)
    python scripts/i18n_report.py --strict   # exit 1 if anything is missing

English is the reference: every other language is compared against the
English files. The report is informational and exits 0 unless --strict is given.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tensorgoat.core import i18n  # noqa: E402

REFERENCE = i18n.DEFAULT_LANG


def _missing_keys(reference: dict, candidate: dict) -> list[str]:
    have = i18n.flatten(candidate)
    return sorted(key for key in i18n.flatten(reference) if have.get(key) in (None, "", []))


def _hint_levels(path: Path) -> list[int]:
    hints = i18n.load_yaml(path).get("hints") or []
    return sorted(int(entry["level"]) for entry in hints if isinstance(entry, dict))


def build_report(lang: str, repo_root: Path = REPO_ROOT, locales_dir: Path | None = None) -> dict:
    """Return ``{"missing_files": [...], "missing_keys": {file: [keys]}, "notes": [...]}``."""
    package = repo_root / "tensorgoat"
    locales = locales_dir or package / "locales"
    missing_files: list[str] = []
    missing_keys: dict[str, list[str]] = {}
    notes: list[str] = []

    def rel(path: Path) -> str:
        try:
            return path.relative_to(repo_root).as_posix()
        except ValueError:
            return path.as_posix()

    def check_yaml(reference: Path, candidate: Path) -> None:
        if not candidate.is_file():
            missing_files.append(rel(candidate))
            return
        keys = _missing_keys(i18n.load_yaml(reference), i18n.load_yaml(candidate))
        if keys:
            missing_keys[rel(candidate)] = keys

    def check_file(candidate: Path) -> None:
        if not candidate.is_file() or not candidate.read_text(encoding="utf-8").strip():
            missing_files.append(rel(candidate))

    check_yaml(locales / f"{REFERENCE}.yml", locales / f"{lang}.yml")

    scenario_dirs = sorted(p for p in (package / "scenarios").iterdir() if p.is_dir())
    for folder in scenario_dirs:
        if not (folder / "scenario.yml").is_file():
            continue
        check_file(folder / f"BRIEFING.{lang}.md")
        check_yaml(folder / f"i18n.{REFERENCE}.yml", folder / f"i18n.{lang}.yml")
        hints = folder / f"hints.{lang}.yml"
        if not hints.is_file():
            missing_files.append(rel(hints))
        elif _hint_levels(hints) != _hint_levels(folder / f"hints.{REFERENCE}.yml"):
            notes.append(f"{rel(hints)}: hint levels differ from the English file")
        solution = repo_root / "solutions" / folder.name
        if solution.is_dir():
            check_file(solution / f"WALKTHROUGH.{lang}.md")

    if lang != REFERENCE:
        readme = repo_root / f"README.{lang}.md"
        if (repo_root / "README.md").is_file() and not readme.is_file():
            missing_files.append(rel(readme))
        glossary_dir = repo_root / "docs" / lang
        if (repo_root / "docs").is_dir() and not any(glossary_dir.glob("*.md")):
            notes.append(f"docs/{lang}/: no glossary yet (see docs/TRANSLATING.md)")

    return {"missing_files": missing_files, "missing_keys": missing_keys, "notes": notes}


def is_complete(report: dict) -> bool:
    return not report["missing_files"] and not report["missing_keys"]


def render(lang: str, report: dict) -> str:
    lines = [f"== {lang} =="]
    if is_complete(report) and not report["notes"]:
        lines.append("  complete")
    for path in report["missing_files"]:
        lines.append(f"  missing file: {path}")
    for path, keys in report["missing_keys"].items():
        lines.append(f"  missing keys in {path}:")
        lines += [f"    - {key}" for key in keys]
    for note in report["notes"]:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lang", action="append", help="language code to check (repeatable)")
    parser.add_argument("--strict", action="store_true", help="exit 1 if anything is missing")
    args = parser.parse_args(argv)

    languages = args.lang or i18n.available_languages()
    complete = True
    for lang in languages:
        report = build_report(i18n.normalize(lang))
        complete = complete and is_complete(report)
        print(render(lang, report))
    return 1 if args.strict and not complete else 0


if __name__ == "__main__":
    raise SystemExit(main())
