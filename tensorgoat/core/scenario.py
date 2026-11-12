"""Scenario base class, generation context and the auto-discovering registry.

A scenario is a folder with a language-independent ``scenario.yml``, a
``generate.py`` exposing ``generate(ctx)``, and (for service scenarios) a
``service.py`` exposing ``create_app(flag_provider, params, default_lang)``.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from tensorgoat.core import flags
from tensorgoat.core.i18n import load_yaml
from tensorgoat.core.numpy_nn import save_npz
from tensorgoat.core.state import State

DIFFICULTIES = ("intro", "easy", "easy-medium", "medium")
TYPES = ("artifact", "service")
ID_PATTERN = re.compile(r"^s\d{2}_[a-z0-9_]+$")

REQUIRED_FILES = ("scenario.yml", "generate.py", "BRIEFING.en.md", "hints.en.yml", "i18n.en.yml")
SERVICE_FILES = ("service.py",)

PARAMS_FILE = "params.json"
ARRAYS_FILE = "arrays.npz"


class ScenarioNotFound(KeyError):
    """Raised when a name matches no scenario id or slug."""


def validate_meta(meta: dict[str, Any], folder_name: str | None = None) -> list[str]:
    """Check a ``scenario.yml`` mapping against the schema; return the problems."""
    problems: list[str] = []
    sid = meta.get("id")
    slug = meta.get("slug")
    if not isinstance(sid, str) or not ID_PATTERN.match(sid):
        problems.append("id must look like 's02_pickle_jar'")
    if not isinstance(slug, str) or not re.match(r"^[a-z0-9_]+$", slug or ""):
        problems.append("slug must be lowercase letters, digits and underscores")
    if isinstance(sid, str) and isinstance(slug, str) and sid[4:] != slug:
        problems.append("id must be 'sNN_' followed by the slug")
    if folder_name is not None and sid != folder_name:
        problems.append("id must equal the folder name")
    if meta.get("difficulty") not in DIFFICULTIES:
        problems.append(f"difficulty must be one of {DIFFICULTIES}")
    if meta.get("type") not in TYPES:
        problems.append(f"type must be one of {TYPES}")
    minutes = meta.get("estimated_time_minutes")
    if not isinstance(minutes, int) or minutes <= 0:
        problems.append("estimated_time_minutes must be a positive integer")
    port = meta.get("port")
    if meta.get("type") == "service":
        if not isinstance(port, int) or not 1024 <= port <= 65535:
            problems.append("service scenarios need a port between 1024 and 65535")
    elif port is not None:
        problems.append("artifact scenarios must have port: null")
    for key in ("categories", "tools_suggested"):
        value = meta.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            problems.append(f"{key} must be a list of strings")
    if not meta.get("categories"):
        problems.append("categories must not be empty")
    if not isinstance(meta.get("tunable_params", {}), dict):
        problems.append("tunable_params must be a mapping")
    return problems


@dataclass
class GenerationContext:
    """Everything ``generate(ctx)`` needs to build a scenario deterministically."""

    scenario_id: str
    slug: str
    flag: str
    seed: int
    params: dict[str, Any]
    workspace: Path
    internal: Path
    assets: Path

    def rng(self, stream: str = "") -> np.random.Generator:
        """A named, independent random stream derived from the scenario seed."""
        digest = hashlib.sha256(f"{self.seed}:{stream}".encode()).digest()
        return np.random.default_rng(int.from_bytes(digest[:8], "big"))

    def asset_text(self, name: str) -> str:
        return (self.assets / name).read_text(encoding="utf-8")

    def write_text(self, name: str, text: str) -> Path:
        """Write a workspace text file with ``\\n`` newlines on every platform."""
        path = self.workspace / name
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def save_service_params(
        self, values: dict[str, Any], arrays: dict[str, np.ndarray] | None = None
    ) -> None:
        """Persist what the service needs (JSON values plus optional numpy arrays)."""
        self.internal.mkdir(parents=True, exist_ok=True)
        text = json.dumps(values, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        (self.internal / PARAMS_FILE).write_text(text, encoding="utf-8", newline="\n")
        if arrays:
            save_npz(self.internal / ARRAYS_FILE, arrays)


def load_service_params(internal: Path) -> dict[str, Any]:
    """Load the ``params`` dict handed to a scenario's ``create_app``."""
    params: dict[str, Any] = json.loads((internal / PARAMS_FILE).read_text(encoding="utf-8"))
    arrays_path = internal / ARRAYS_FILE
    if arrays_path.is_file():
        with np.load(arrays_path) as data:
            params.update({key: data[key] for key in data.files})
    return params


@dataclass(frozen=True)
class Scenario:
    """Language-independent description of one scenario (from ``scenario.yml``)."""

    id: str
    slug: str
    difficulty: str
    type: str
    estimated_time_minutes: int
    port: int | None
    categories: tuple[str, ...]
    tools_suggested: tuple[str, ...]
    path: Path
    tunable_params: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_dir(cls, path: Path) -> Scenario:
        meta = load_yaml(path / "scenario.yml")
        problems = validate_meta(meta, folder_name=path.name)
        if problems:
            raise ValueError(f"{path.name}/scenario.yml: " + "; ".join(problems))
        return cls(
            id=meta["id"],
            slug=meta["slug"],
            difficulty=meta["difficulty"],
            type=meta["type"],
            estimated_time_minutes=meta["estimated_time_minutes"],
            port=meta.get("port"),
            categories=tuple(meta["categories"]),
            tools_suggested=tuple(meta.get("tools_suggested") or ()),
            path=path,
            tunable_params=dict(meta.get("tunable_params") or {}),
        )

    @property
    def is_service(self) -> bool:
        return self.type == "service"

    def _module(self, name: str) -> Any:
        return importlib.import_module(f"tensorgoat.scenarios.{self.id}.{name}")

    def flag(self, state: State) -> str:
        return flags.make_flag(state.install_secret(), self.id, self.slug)

    def generate(self, state: State) -> GenerationContext:
        """(Re)build this scenario's artefacts for the given state directory."""
        secret = state.install_secret()
        ctx = GenerationContext(
            scenario_id=self.id,
            slug=self.slug,
            flag=flags.make_flag(secret, self.id, self.slug),
            seed=flags.scenario_seed(secret, self.id),
            params=dict(self.tunable_params),
            workspace=state.workspace_dir(self.id),
            internal=state.internal_dir(self.id),
            assets=self.path / "assets",
        )
        ctx.workspace.mkdir(parents=True, exist_ok=True)
        ctx.internal.mkdir(parents=True, exist_ok=True)
        self._module("generate").generate(ctx)
        return ctx

    def create_app(
        self,
        state: State,
        default_lang: str = "en",
        params: dict[str, Any] | None = None,
        flag_provider: Callable[[], str] | None = None,
    ) -> Any:
        """Build the FastAPI app of a service scenario from generated artefacts."""
        if not self.is_service:
            raise ValueError(f"{self.id} is not a service scenario")
        if params is None:
            params = load_service_params(state.internal_dir(self.id))
        if flag_provider is None:
            flag = self.flag(state)

            def flag_provider() -> str:
                return flag

        return self._module("service").create_app(flag_provider, params, default_lang)


class Registry:
    """Discovers every scenario folder below ``root`` (no hard-coded list)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._scenarios: list[Scenario] | None = None

    def all(self) -> list[Scenario]:
        if self._scenarios is None:
            folders = sorted(p for p in self.root.iterdir() if (p / "scenario.yml").is_file())
            self._scenarios = [Scenario.from_dir(folder) for folder in folders]
        return list(self._scenarios)

    def get(self, name: str) -> Scenario:
        """Find a scenario by full id (``s02_pickle_jar``), slug or ``s02`` prefix."""
        wanted = name.strip().lower().replace("-", "_")
        for scenario in self.all():
            if wanted in (scenario.id, scenario.slug, scenario.id[:3]):
                return scenario
        raise ScenarioNotFound(name)

    def services(self) -> list[Scenario]:
        return [scenario for scenario in self.all() if scenario.is_service]
