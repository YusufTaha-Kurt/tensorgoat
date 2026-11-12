from __future__ import annotations

from pathlib import Path

import yaml

from tensorgoat.core.state import State, home_dir


def test_home_dir_honours_env(isolated_home: Path, monkeypatch):
    assert home_dir() == isolated_home
    monkeypatch.delenv("TENSORGOAT_HOME")
    assert home_dir() == Path.home() / ".tensorgoat"


def test_config_is_created_on_first_use(state: State):
    assert not state.config_path.exists()
    config = state.load_config()
    assert len(config["install_secret"]) == 64
    assert (
        yaml.safe_load(state.config_path.read_text())["install_secret"]
        == (config["install_secret"])
    )


def test_lang_preference_roundtrip(state: State):
    assert state.get_lang() is None
    state.set_lang("tr")
    assert State(state.home).get_lang() == "tr"


def test_records_have_defaults_and_persist(state: State):
    assert state.record("s00_first_flag") == {
        "created": False,
        "mode": None,
        "port": None,
        "pid": None,
        "solved": False,
        "hints_unlocked": 0,
    }
    state.update_record("s00_first_flag", created=True, hints_unlocked=2)
    state.update_record("s00_first_flag", solved=True)
    record = State(state.home).record("s00_first_flag")
    assert record["created"] and record["solved"] and record["hints_unlocked"] == 2
    assert list(state.records()) == ["s00_first_flag"]


def test_corrupt_state_file_is_tolerated(state: State):
    state.home.mkdir(parents=True)
    state.state_path.write_text("{not json", encoding="utf-8")
    assert state.records() == {}


def test_reset_removes_everything(state: State):
    state.load_config()
    state.update_record("s00_first_flag", created=True)
    state.workspace_dir("s00_first_flag").mkdir(parents=True)
    state.internal_dir("s00_first_flag").mkdir(parents=True)
    state.reset()
    assert not state.config_path.exists()
    assert not state.state_path.exists()
    assert not state.workspace_root.exists()
    assert not state.internal_root.exists()
