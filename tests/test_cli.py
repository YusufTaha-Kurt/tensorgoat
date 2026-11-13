"""End-to-end behaviour of the CLI commands."""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

from helpers import invoke

from tensorgoat import __version__
from tensorgoat.core import i18n
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

EN = i18n.Translator("en")
S00 = "s00_first_flag"


def text(key: str, **values) -> str:
    return EN.t(key, **values)


def test_list_shows_every_scenario():
    result = invoke("list")
    assert result.exit_code == 0, result.output
    for scenario in all_scenarios():
        assert scenario.id in result.output
        assert i18n.load_yaml(scenario.path / "i18n.en.yml")["title"] in result.output
    assert text("list.status_solved") not in result.output


def test_version():
    result = invoke("--version")
    assert result.exit_code == 0 and __version__ in result.output


def test_create_generates_workspace_and_shows_briefing(state: State):
    result = invoke("create", "first_flag")
    assert result.exit_code == 0, result.output
    workspace = state.workspace_dir(S00)
    assert (workspace / "model_card.md").is_file()
    assert text("create.next_steps_title") in result.output
    assert "Welcome, recruit" in result.output
    assert "tensorgoat hint first_flag" in result.output
    assert "tensorgoat submit first_flag" in result.output
    assert workspace.name in result.output
    assert state.record(S00)["created"] is True


def test_scenario_can_be_named_by_id_slug_or_prefix(state: State):
    for name in ("s00_first_flag", "first_flag", "FIRST-FLAG", "s00"):
        assert invoke("briefing", name).exit_code == 0, name
    result = invoke("briefing", "no_such_scenario")
    assert result.exit_code == 2
    assert "no_such_scenario" in result.output


def test_create_is_idempotent_and_keeps_player_files(state: State):
    assert invoke("create", S00).exit_code == 0
    notes = state.workspace_dir(S00) / "my_notes.txt"
    notes.write_text("remember this", encoding="utf-8")
    assert invoke("create", S00).exit_code == 0
    assert notes.read_text(encoding="utf-8") == "remember this"


def test_briefing_shows_story_and_metadata():
    result = invoke("briefing", S00)
    scenario = get_scenario(S00)
    assert result.exit_code == 0
    assert "Welcome, recruit" in result.output
    assert scenario.categories[0] in result.output
    assert text("difficulty.intro") in result.output


def test_hints_are_tiered(state: State):
    hints, _ = i18n.load_hints(get_scenario(S00).path, "en")

    first = invoke("hint", S00)
    assert first.exit_code == 0 and hints[0] in first.output
    assert state.record(S00)["hints_unlocked"] == 1

    # Asking for level 3 before level 2: declining shows nothing.
    declined = invoke("hint", S00, "3", input="n\n")
    assert declined.exit_code == 1
    assert hints[1] not in declined.output and hints[2] not in declined.output
    assert state.record(S00)["hints_unlocked"] == 1

    # Accepting opens the previous level (2), not the requested one.
    accepted = invoke("hint", S00, "3", input="y\n")
    assert accepted.exit_code == 0
    assert hints[1] in accepted.output and hints[2] not in accepted.output
    assert state.record(S00)["hints_unlocked"] == 2

    third = invoke("hint", S00, "3")
    assert third.exit_code == 0 and hints[2] in third.output
    assert state.record(S00)["hints_unlocked"] == 3

    again = invoke("hint", S00, "1")
    assert again.exit_code == 0 and hints[0] in again.output
    assert state.record(S00)["hints_unlocked"] == 3
    assert invoke("hint", S00, "4").exit_code == 2


def test_hint_without_level_opens_the_next_one(state: State):
    hints, _ = i18n.load_hints(get_scenario(S00).path, "en")
    for expected in (hints[0], hints[1], hints[2], hints[2]):
        result = invoke("hint", "first_flag")
        assert result.exit_code == 0 and expected in result.output


def test_submit_wrong_then_right(state: State):
    scenario = get_scenario(S00)
    wrong = invoke("submit", S00, "TGOAT{first_flag_000000000000}")
    assert wrong.exit_code == 1
    assert state.record(S00)["solved"] is False

    right = invoke("submit", "first_flag", scenario.flag(state))
    assert right.exit_code == 0, right.output
    assert state.record(S00)["solved"] is True
    assert text("list.status_solved") in invoke("list").output

    # Another scenario's flag must not be accepted.
    other = get_scenario("s01_hidden_weights")
    assert invoke("submit", S00, other.flag(state)).exit_code == 1


def test_destroy_removes_workspace_but_keeps_progress(state: State):
    scenario = get_scenario(S00)
    invoke("create", S00)
    invoke("submit", S00, scenario.flag(state))
    result = invoke("destroy", S00)
    assert result.exit_code == 0, result.output
    assert not state.workspace_dir(S00).exists()
    record = state.record(S00)
    assert record["created"] is False and record["solved"] is True

    again = invoke("destroy", S00)
    assert again.exit_code == 0
    assert text("destroy.not_created", id=S00) in again.output
    assert invoke("destroy").exit_code == 2


def test_destroy_all(state: State):
    assert text("destroy.nothing") in invoke("destroy", "--all").output
    invoke("create", S00)
    invoke("create", "s01_hidden_weights")
    result = invoke("destroy", "--all")
    assert result.exit_code == 0, result.output
    assert not state.workspace_root.exists() or not any(state.workspace_root.iterdir())
    assert all(not record["created"] for record in state.records().values())


def test_status_without_services():
    result = invoke("status")
    assert result.exit_code == 0
    assert text("status.none") in result.output


def test_lang_command(state: State):
    shown = invoke("lang")
    assert shown.exit_code == 0 and "en" in shown.output
    unknown = invoke("lang", "zz")
    assert unknown.exit_code == 2
    assert state.get_lang() is None
    assert invoke("lang", "en").exit_code == 0
    assert state.get_lang() == "en"


def test_reset_asks_for_confirmation(state: State):
    invoke("create", S00)
    cancelled = invoke("reset", input="n\n")
    assert cancelled.exit_code == 1
    assert state.workspace_dir(S00).exists()

    done = invoke("reset", "--yes")
    assert done.exit_code == 0, done.output
    assert not state.workspace_root.exists()
    assert not state.state_path.exists() and not state.config_path.exists()


def test_reset_only_deletes_tensorgoat_files(state: State):
    invoke("create", S00)
    foreign = state.home / "not_ours.txt"
    foreign.write_text("keep me", encoding="utf-8")
    assert invoke("reset", "--yes").exit_code == 0
    assert foreign.read_text(encoding="utf-8") == "keep me"


def test_both_console_scripts_point_to_the_same_entry():
    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts.get("tensorgoat") == "tensorgoat.cli:main"
    assert scripts.get("tgoat") == "tensorgoat.cli:main"


def test_tgoat_alias_runs():
    bin_dir = Path(sys.executable).parent
    tgoat = shutil.which("tgoat", path=str(bin_dir)) or shutil.which("tgoat")
    assert tgoat, "the tgoat console script is not installed"
    result = subprocess.run(
        [tgoat, "list"], capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert "s00_first_flag" in result.stdout
    module = subprocess.run(
        [sys.executable, "-m", "tensorgoat", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert module.returncode == 0 and __version__ in module.stdout


# ----------------------------------------------------------- service lifecycle
def test_service_lifecycle_create_status_restart_destroy(state: State):
    import httpx
    from helpers import free_port

    sid = "s03_model_heist"
    port = free_port()
    url = f"http://127.0.0.1:{port}"

    created = invoke("create", "model_heist", "--port", str(port))
    assert created.exit_code == 0, created.output
    assert url in created.output
    record = state.record(sid)
    assert record["mode"] == "native" and record["port"] == port and record["pid"]

    shown = invoke("status")
    assert shown.exit_code == 0
    assert sid in shown.output and url in shown.output
    assert text("status.running") in shown.output

    # Use one query, then create again: the service restarts and the budget resets.
    assert httpx.post(f"{url}/score", json={"features": [0.5] * 5}).status_code == 200
    assert httpx.get(f"{url}/").json()["queries_remaining"] == 49
    assert invoke("create", sid, "--port", str(port)).exit_code == 0
    assert httpx.get(f"{url}/").json()["queries_remaining"] == 50

    destroyed = invoke("destroy", sid)
    assert destroyed.exit_code == 0, destroyed.output
    with_error = None
    try:
        httpx.get(f"{url}/", timeout=2)
    except httpx.HTTPError as error:
        with_error = error
    assert with_error is not None, "the service must be stopped by destroy"
    assert not state.workspace_dir(sid).exists() and not state.internal_dir(sid).exists()
    assert text("status.none") in invoke("status").output


def test_create_reports_a_busy_port(state: State):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        result = invoke("create", "model_heist", "--port", str(port))
    assert result.exit_code == 1
    assert str(port) in result.output
    assert state.record("s03_model_heist")["mode"] is None
    assert invoke("destroy", "model_heist").exit_code == 0


def test_port_cannot_be_combined_with_docker():
    result = invoke("create", "model_heist", "--docker", "--port", "9999")
    assert result.exit_code == 1
    assert text("errors.port_with_docker") in result.output


def test_service_speaks_the_cli_language(state: State):
    """The CLI starts services with the active language as their default."""
    from helpers import free_port

    from tensorgoat.core import runner

    port = free_port()
    assert invoke("--lang", "en", "create", "model_heist", "--port", str(port)).exit_code == 0
    try:
        description = i18n.load_yaml(get_scenario("model_heist").path / "i18n.en.yml")["messages"][
            "description"
        ]
        assert runner.probe(port)["message"] == description
    finally:
        invoke("destroy", "model_heist")
