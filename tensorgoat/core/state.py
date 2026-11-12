"""State directory management (``~/.tensorgoat`` or ``$TENSORGOAT_HOME``).

Layout::

    config.yml               install_secret (32 bytes, hex) and the ``lang`` preference
    state.json               per-scenario records: created, mode, port, pid, solved, hints
    workspace/<scenario_id>  files the player works with
    internal/<scenario_id>   service-side artefacts (models, logs) the player should not need
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
from pathlib import Path
from typing import Any

import yaml

from tensorgoat.core import flags

HOME_ENV = "TENSORGOAT_HOME"
SEED_ENV = "TENSORGOAT_SEED"
LANG_ENV = "TENSORGOAT_LANG"


def home_dir() -> Path:
    """Resolve the state directory, honouring ``TENSORGOAT_HOME``."""
    override = os.environ.get(HOME_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".tensorgoat"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class State:
    """Read/write access to everything TensorGoat persists between commands."""

    def __init__(self, home: Path | None = None) -> None:
        self.home = Path(home) if home is not None else home_dir()

    # ------------------------------------------------------------------ paths
    @property
    def config_path(self) -> Path:
        return self.home / "config.yml"

    @property
    def state_path(self) -> Path:
        return self.home / "state.json"

    @property
    def workspace_root(self) -> Path:
        return self.home / "workspace"

    @property
    def internal_root(self) -> Path:
        return self.home / "internal"

    def workspace_dir(self, scenario_id: str) -> Path:
        return self.workspace_root / scenario_id

    def internal_dir(self, scenario_id: str) -> Path:
        return self.internal_root / scenario_id

    # ----------------------------------------------------------------- config
    def load_config(self) -> dict[str, Any]:
        """Load ``config.yml``, creating it (with a fresh secret) on first run."""
        config: dict[str, Any] = {}
        if self.config_path.is_file():
            loaded = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = loaded
        if not _is_valid_secret(config.get("install_secret")):
            config["install_secret"] = secrets.token_hex(32)
            self.save_config(config)
        return config

    def save_config(self, config: dict[str, Any]) -> None:
        _atomic_write(self.config_path, yaml.safe_dump(config, sort_keys=True))

    def install_secret(self) -> str:
        """The per-install secret. ``TENSORGOAT_SEED`` overrides it deterministically."""
        seed = os.environ.get(SEED_ENV, "")
        if seed:
            return flags.derive_secret_from_seed(seed)
        return str(self.load_config()["install_secret"])

    def get_lang(self) -> str | None:
        if not self.config_path.is_file():
            return None
        lang = self.load_config().get("lang")
        return str(lang) if lang else None

    def set_lang(self, lang: str) -> None:
        config = self.load_config()
        config["lang"] = lang
        self.save_config(config)

    # ------------------------------------------------------------------ state
    def load_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            if isinstance(data, dict) and isinstance(data.get("scenarios"), dict):
                return data
        return {"scenarios": {}}

    def save_state(self, data: dict[str, Any]) -> None:
        _atomic_write(self.state_path, json.dumps(data, indent=2, sort_keys=True) + "\n")

    def record(self, scenario_id: str) -> dict[str, Any]:
        """Return the record of one scenario (with defaults filled in)."""
        stored = self.load_state()["scenarios"].get(scenario_id, {})
        return {**_default_record(), **stored}

    def update_record(self, scenario_id: str, **fields: Any) -> dict[str, Any]:
        data = self.load_state()
        record = {**_default_record(), **data["scenarios"].get(scenario_id, {}), **fields}
        data["scenarios"][scenario_id] = record
        self.save_state(data)
        return record

    def records(self) -> dict[str, dict[str, Any]]:
        stored = self.load_state()["scenarios"]
        return {sid: {**_default_record(), **rec} for sid, rec in stored.items()}

    # ---------------------------------------------------------------- cleanup
    def remove_scenario_files(self, scenario_id: str) -> None:
        shutil.rmtree(self.workspace_dir(scenario_id), ignore_errors=True)
        shutil.rmtree(self.internal_dir(scenario_id), ignore_errors=True)

    def reset(self) -> None:
        """Delete everything TensorGoat created (config, state, workspaces)."""
        shutil.rmtree(self.workspace_root, ignore_errors=True)
        shutil.rmtree(self.internal_root, ignore_errors=True)
        for path in (self.config_path, self.state_path):
            path.unlink(missing_ok=True)


def _default_record() -> dict[str, Any]:
    return {
        "created": False,
        "mode": None,
        "port": None,
        "pid": None,
        "solved": False,
        "hints_unlocked": 0,
    }


def _is_valid_secret(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True
