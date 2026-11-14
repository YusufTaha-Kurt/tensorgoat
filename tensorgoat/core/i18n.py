"""Language selection, text catalogues and the fall-back-to-English rule.

No player-facing text lives in Python code. Everything is read from
language-suffixed files:

* ``tensorgoat/locales/<lang>.yml``        CLI interface texts
* ``<scenario>/BRIEFING.<lang>.md``        scenario story
* ``<scenario>/hints.<lang>.yml``          three hint tiers
* ``<scenario>/i18n.<lang>.yml``           title, objectives, service messages

Adding a language means adding files, never touching code: the list of
available languages is discovered from ``locales/*.yml``.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

DEFAULT_LANG = "en"
LANG_ENV = "TENSORGOAT_LANG"
LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


# ------------------------------------------------------------------ primitives
def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping; a missing or empty file yields an empty dict."""
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def normalize(code: str | None) -> str:
    """``"TR"`` -> ``"tr"``, ``"pt_BR"`` -> ``"pt-br"``; empty input -> ``""``."""
    return (code or "").strip().lower().replace("_", "-")


def format_text(text: str, values: Mapping[str, Any]) -> str:
    """Fill ``{placeholders}``; catalogue texts write literal braces as ``{{ }}``.

    A broken placeholder in a translation must never crash the CLI or a
    service, so formatting errors fall back to the raw text.
    """
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        return text


def lookup(data: Mapping[str, Any], dotted_key: str) -> Any:
    """Resolve ``"a.b.c"`` inside nested mappings; ``None`` when absent."""
    node: Any = data
    for part in dotted_key.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    return node


def flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested mappings to ``{"a.b.c": leaf}`` (lists count as leaves)."""
    flat: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(flatten(value, dotted + "."))
        else:
            flat[dotted] = value
    return flat


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Overlay ``override`` on ``base`` (empty/None override values are ignored)."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = deep_merge(merged[key], value)
        elif value not in (None, "", [], {}):
            merged[key] = value
    return merged


# ------------------------------------------------------------ language choice
def available_languages(locales_dir: Path | None = None) -> list[str]:
    """Languages discovered from ``locales/*.yml`` (English first)."""
    directory = locales_dir or LOCALES_DIR
    found = sorted(normalize(path.stem) for path in directory.glob("*.yml"))
    return sorted(found, key=lambda code: (code != DEFAULT_LANG, code))


def resolve_language(
    cli_lang: str | None = None,
    config_lang: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Priority: ``--lang`` > ``TENSORGOAT_LANG`` > ``config.yml`` > English.

    The system locale (``LANG`` / ``LC_ALL``) is deliberately ignored: players
    see English unless they explicitly choose otherwise.
    """
    env = os.environ if environ is None else environ
    for candidate in (cli_lang, env.get(LANG_ENV), config_lang):
        code = normalize(candidate)
        if code:
            return code
    return DEFAULT_LANG


def negotiate_language(header: str | None, available: Iterable[str], default: str) -> str:
    """Pick a language from an ``Accept-Language`` header (services use this)."""
    choices = {normalize(code) for code in available}
    ranked: list[tuple[float, int, str]] = []
    for position, part in enumerate((header or "").split(",")):
        tag, _, params = part.strip().partition(";")
        tag = normalize(tag)
        if not tag or tag == "*":
            continue
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 0.0
        ranked.append((-quality, position, tag))
    for _, _, tag in sorted(ranked):
        if tag in choices:
            return tag
        primary = tag.split("-")[0]
        if primary in choices:
            return primary
    return normalize(default) or DEFAULT_LANG


# ------------------------------------------------------- language-tagged files
def localized_path(directory: Path, stem: str, suffix: str, lang: str) -> tuple[Path, bool]:
    """Return ``(<stem>.<lang>.<suffix>, fell_back)``, falling back to English."""
    wanted = directory / f"{stem}.{normalize(lang)}.{suffix}"
    if wanted.is_file():
        return wanted, False
    return directory / f"{stem}.{DEFAULT_LANG}.{suffix}", normalize(lang) != DEFAULT_LANG


def load_scenario_texts(directory: Path, lang: str) -> tuple[dict[str, Any], bool]:
    """Merge ``i18n.en.yml`` with ``i18n.<lang>.yml``; report if English filled gaps."""
    english = load_yaml(directory / f"i18n.{DEFAULT_LANG}.yml")
    code = normalize(lang)
    if code == DEFAULT_LANG:
        return english, False
    local = load_yaml(directory / f"i18n.{code}.yml")
    local_flat = flatten(local)
    missing = [key for key in flatten(english) if local_flat.get(key) in (None, "", [])]
    return deep_merge(english, local), bool(missing)


def _hint_levels(directory: Path, lang: str) -> dict[int, str]:
    data = load_yaml(directory / f"hints.{normalize(lang)}.yml")
    levels: dict[int, str] = {}
    for entry in data.get("hints") or []:
        if isinstance(entry, Mapping) and "level" in entry:
            levels[int(entry["level"])] = str(entry.get("text") or "").strip()
    return levels


def load_hints(directory: Path, lang: str) -> tuple[list[str], bool]:
    """Hint texts ordered by level; tiers missing in ``lang`` come from English."""
    english = _hint_levels(directory, DEFAULT_LANG)
    code = normalize(lang)
    if code == DEFAULT_LANG:
        return [english[level] for level in sorted(english)], False
    local = _hint_levels(directory, code)
    fell_back = False
    texts: list[str] = []
    for level in sorted(english):
        if local.get(level):
            texts.append(local[level])
        else:
            texts.append(english[level])
            fell_back = True
    return texts, fell_back


# ------------------------------------------------------------------ translator
class Translator:
    """Looks up texts in the active language and remembers if English was used."""

    def __init__(self, lang: str | None = None, locales_dir: Path | None = None) -> None:
        self.lang = normalize(lang) or DEFAULT_LANG
        self.fallback_used = False
        directory = locales_dir or LOCALES_DIR
        self._english = load_yaml(directory / f"{DEFAULT_LANG}.yml")
        self._local: dict[str, Any] = {}
        if self.lang != DEFAULT_LANG:
            self._local = load_yaml(directory / f"{self.lang}.yml")

    def raw(self, key: str) -> str:
        """The catalogue text of ``key`` as written, placeholders not filled in."""
        text = lookup(self._local, key) if self.lang != DEFAULT_LANG else None
        if text in (None, ""):
            if self.lang != DEFAULT_LANG:
                self.fallback_used = True
            text = lookup(self._english, key)
        return key if text is None else str(text)

    def t(self, key: str, **values: Any) -> str:
        """Translate ``key``; ``values`` fill ``{placeholders}`` in the text."""
        return format_text(self.raw(key), values)

    def file_text(self, directory: Path, stem: str, suffix: str) -> str:
        path, fell_back = localized_path(directory, stem, suffix, self.lang)
        self.fallback_used = self.fallback_used or fell_back
        return path.read_text(encoding="utf-8")

    def scenario_texts(self, directory: Path) -> dict[str, Any]:
        texts, fell_back = load_scenario_texts(directory, self.lang)
        self.fallback_used = self.fallback_used or fell_back
        return texts

    def hints(self, directory: Path) -> list[str]:
        texts, fell_back = load_hints(directory, self.lang)
        self.fallback_used = self.fallback_used or fell_back
        return texts
