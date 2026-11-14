"""The local web interface (``tensorgoat ui``): behaviour, texts and safety rules."""

from __future__ import annotations

import re
import socket
import subprocess
import sys
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from helpers import REPO_ROOT, free_port, invoke

from tensorgoat.core import i18n, ops, runner
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario
from tensorgoat.web import server

TOKEN = "test-token"
BASE_URL = "http://127.0.0.1:8100"
STATIC = REPO_ROOT / "tensorgoat" / "web" / "static"
EN_UI = i18n.load_yaml(REPO_ROOT / "tensorgoat" / "locales" / "en.yml")["ui"]
S00 = "s00_first_flag"


@pytest.fixture
def ui(state: State) -> TestClient:
    client = TestClient(server.create_ui_app(state, "en", token=TOKEN), base_url=BASE_URL)
    client.headers["X-TGoat-Token"] = TOKEN
    return client


# ------------------------------------------------------------------- safety
def test_page_carries_the_token_and_its_assets(ui):
    page = ui.get("/")
    assert page.status_code == 200 and TOKEN in page.text
    assert server.TOKEN_PLACEHOLDER not in page.text
    assert page.headers["cache-control"] == "no-store"
    for name in ("app.js", "style.css"):
        assert ui.get(f"/static/{name}").status_code == 200
    assert ui.get("/static/server.py").status_code == 404


def test_api_requires_the_token(state):
    client = TestClient(server.create_ui_app(state, "en", token=TOKEN), base_url=BASE_URL)
    assert client.get("/").status_code == 200, "the page itself needs no token"
    assert client.get("/api/overview").status_code == 403
    wrong = client.get("/api/overview", headers={"X-TGoat-Token": "guess"})
    assert wrong.status_code == 403 and wrong.json()["error"] == "ui.error_forbidden"
    assert client.post(f"/api/scenarios/{S00}/create", json={}).status_code == 403
    assert not State(state.home).record(S00)["created"]


def test_every_run_gets_its_own_token(state):
    first = TestClient(server.create_ui_app(state), base_url=BASE_URL).get("/").text
    second = TestClient(server.create_ui_app(state), base_url=BASE_URL).get("/").text
    token = re.search(r'TGOAT_TOKEN = "([^"]+)"', first).group(1)
    assert len(token) >= 24 and token not in second


def test_requests_for_another_host_are_rejected(ui):
    """DNS rebinding: a foreign name that resolves to 127.0.0.1 must get nothing."""
    for path in ("/", "/api/overview", "/static/app.js"):
        response = ui.get(path, headers={"Host": "attacker.example:8100"})
        assert response.status_code == 403, path
        assert TOKEN not in response.text
    assert ui.get("/api/overview", headers={"Host": "localhost:8100"}).status_code == 200


def test_interface_listens_on_localhost_only():
    source = (REPO_ROOT / "tensorgoat" / "web" / "server.py").read_text(encoding="utf-8")
    assert "host=runner.BIND_HOST" in source and "0.0.0.0" not in source
    assert runner.BIND_HOST == "127.0.0.1"


def test_static_files_work_offline():
    for path in STATIC.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "://" not in text, f"{path.name} must not load anything from a network address"
        assert "@import" not in text


# -------------------------------------------------------------------- texts
def _keys_used_by_the_page() -> set[str]:
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    keys = set(re.findall(r"""\bt\(\s*["']([a-z0-9_]+)["']\s*[,)]""", script))
    keys |= set(re.findall(r'data-i18n="([a-z0-9_]+)"', page))
    return keys


def test_page_uses_only_catalogue_keys_and_no_key_is_dead():
    used = _keys_used_by_the_page()
    assert len(used) > 50, "key extraction looks broken"
    missing = sorted(key for key in used if key not in EN_UI)
    assert not missing, f"keys missing from the ui section of locales/en.yml: {missing}"

    script = (STATIC / "app.js").read_text(encoding="utf-8")
    backend = (REPO_ROOT / "tensorgoat" / "web" / "server.py").read_text(encoding="utf-8")
    # Keys the page builds at run time: t("status_" + ...), t("how_" + n + "_title").
    dynamic = [m + "_" for m in re.findall(r"""\bt\(\s*["']([a-z]+)_["']\s*\+""", script)]
    assert set(dynamic) == {"how_", "status_"}
    dead = [
        key
        for key in EN_UI
        if key not in used and f'"ui.{key}"' not in backend and not key.startswith(tuple(dynamic))
    ]
    assert not dead, f"ui keys nothing refers to: {dead}"


def test_page_has_no_hard_coded_sentences():
    """Text between tags must come from the catalogue (brand name and code aside)."""
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    body = page.split("<body>")[1]
    body = re.sub(r"<script.*?</script>|<svg.*?</svg>", "", body, flags=re.S)
    words = [text.strip() for text in re.findall(r">([^<>]+)<", body) if text.strip()]
    assert words == ["TensorGoat"]


def test_overview_lists_scenarios_and_sends_all_texts(ui):
    data = ui.get("/api/overview").json()
    assert [item["id"] for item in data["scenarios"]] == [s.id for s in all_scenarios()]
    assert data["solved"] == 0 and data["total"] == len(all_scenarios())
    assert data["lang"] == "en" and "en" in data["languages"]
    assert set(data["strings"]) == set(EN_UI)
    assert data["strings"]["flag_placeholder"] == EN_UI["flag_placeholder"], "sent unformatted"
    first = data["scenarios"][0]
    assert first["status"] == "new" and first["title"] and first["summary"]
    assert ui.get("/api/scenarios/nope").status_code == 404


# -------------------------------------------------------------------- flows
def test_artifact_scenario_from_start_to_defence(ui, state):
    scenario = get_scenario(S00)
    before = ui.get(f"/api/scenarios/{S00}").json()
    assert before["created"] is False and before["files"] == [] and before["service"] is None
    assert "<p>" in before["briefing_html"] and before["objectives"] and before["categories"]
    assert before["hints"] == {"total": 3, "opened": []}

    created = ui.post(f"/api/scenarios/{S00}/create", json={}).json()
    assert created["created"] is True and created["status"] == "created"
    assert created["workspace"] == str(state.workspace_dir(S00))
    names = {item["name"]: item for item in created["files"]}
    assert names["model_card.md"]["viewable"] is True

    shown = ui.get(f"/api/scenarios/{S00}/files/model_card.md").json()
    expected = (state.workspace_dir(S00) / "model_card.md").read_text(encoding="utf-8")
    assert shown["text"] == expected

    hints, _ = i18n.load_hints(scenario.path, "en")
    for count in (1, 2, 3, 3):
        opened = ui.post(f"/api/scenarios/{S00}/hint", json={}).json()["hints"]["opened"]
        assert opened == hints[:count]
    assert state.record(S00)["hints_unlocked"] == 3

    locked = ui.get(f"/api/scenarios/{S00}/walkthrough")
    assert locked.status_code == 423 and locked.json()["error"] == "ui.defense_locked"
    revealed = ui.get(f"/api/scenarios/{S00}/walkthrough", params={"reveal": "true"})
    assert revealed.status_code == 200 and "Mitigation / Defense" in revealed.json()["html"]

    wrong = ui.post(f"/api/scenarios/{S00}/submit", json={"flag": "TGOAT{nope_000000000000}"})
    assert wrong.json()["correct"] is False and state.record(S00)["solved"] is False
    right = ui.post(f"/api/scenarios/{S00}/submit", json={"flag": scenario.flag(state)}).json()
    assert right["correct"] is True and right["already_solved"] is False
    assert right["scenario"]["status"] == "solved"
    again = ui.post(f"/api/scenarios/{S00}/submit", json={"flag": scenario.flag(state)}).json()
    assert again["already_solved"] is True
    assert ui.get(f"/api/scenarios/{S00}/walkthrough").status_code == 200
    assert ui.get("/api/overview").json()["solved"] == 1

    destroyed = ui.post(f"/api/scenarios/{S00}/destroy", json={}).json()
    assert destroyed["created"] is False and destroyed["solved"] is True
    assert not state.workspace_dir(S00).exists()


def test_file_view_cannot_leave_the_workspace(ui, state):
    ui.post(f"/api/scenarios/{S00}/create", json={})
    state.set_lang("en")  # makes sure config.yml (with the install secret) exists
    assert state.config_path.is_file()
    for name in ("..%2F..%2Fconfig.yml", "%2e%2e/%2e%2e/config.yml", "..%5C..%5Cconfig.yml"):
        response = ui.get(f"/api/scenarios/{S00}/files/{name}")
        assert response.status_code == 404, name
        assert "install_secret" not in response.text
    assert ui.get(f"/api/scenarios/{S00}/files/missing.txt").status_code == 404


def test_binary_files_are_listed_but_not_shown(ui):
    sid = "s01_hidden_weights"
    created = ui.post(f"/api/scenarios/{sid}/create", json={}).json()
    files = {item["name"]: item for item in created["files"]}
    assert files["classifier.safetensors"]["viewable"] is False
    response = ui.get(f"/api/scenarios/{sid}/files/classifier.safetensors")
    assert response.status_code == 415 and response.json()["error"] == "ui.files_binary"


def test_service_scenario_and_request_console(ui, state):
    sid = "s03_model_heist"
    port = free_port()
    created = ui.post(f"/api/scenarios/{sid}/create", json={"port": port})
    assert created.status_code == 200, created.text
    try:
        service = created.json()["service"]
        assert service == {
            "created": True,
            "running": True,
            "url": f"http://127.0.0.1:{port}",
            "mode": "native",
        }
        root = ui.post(f"/api/scenarios/{sid}/request", json={"method": "GET", "path": "/"})
        assert root.status_code == 200
        assert root.json()["status"] == 200 and root.json()["body"]["scenario"] == sid
        assert "POST /score" in root.json()["body"]["endpoints"]

        request = {"method": "POST", "path": "/score", "body": {"features": [0.5] * 5}}
        scored = ui.post(f"/api/scenarios/{sid}/request", json=request).json()
        assert scored["status"] == 200 and 0 < scored["body"]["approval_probability"] < 1

        # A service error is passed through with its status and error_code.
        request["body"] = {"features": [0.5]}
        failed = ui.post(f"/api/scenarios/{sid}/request", json=request).json()
        assert failed["status"] == 422 and failed["body"]["error_code"] == "INVALID_FEATURES"

        for bad in (
            {"method": "GET", "path": "http://example.com/"},
            {"method": "GET", "path": "@example.com/"},
            {"method": "GET", "path": ""},
            {"method": "DELETE", "path": "/"},
        ):
            response = ui.post(f"/api/scenarios/{sid}/request", json=bad)
            assert response.status_code == 400, bad
    finally:
        destroyed = ui.post(f"/api/scenarios/{sid}/destroy", json={})
    assert destroyed.json()["service"] == {
        "created": False,
        "running": False,
        "url": None,
        "mode": None,
    }
    stopped = ui.post(f"/api/scenarios/{sid}/request", json={"method": "GET", "path": "/"})
    assert stopped.status_code == 409 and stopped.json()["error"] == "ui.console_not_running"
    # Artifact scenarios have no console at all.
    none = ui.post(f"/api/scenarios/{S00}/request", json={"method": "GET", "path": "/"})
    assert none.status_code == 404


def test_console_only_reaches_the_local_service():
    with pytest.raises(ValueError):
        runner.call_service(8103, "GET", "@example.com/")
    with pytest.raises(runner.RunnerError) as error:
        runner.call_service(free_port(), "GET", "/", timeout=2)
    assert error.value.key == "errors.service_unreachable"


def test_a_busy_port_is_reported_in_words(ui):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        response = ui.post("/api/scenarios/s03_model_heist/create", json={"port": port})
    assert response.status_code == 409
    assert response.json()["error"] == "errors.port_in_use"
    assert str(port) in response.json()["message"]
    assert ui.post("/api/scenarios/s03_model_heist/create", json={"port": 80}).status_code == 400
    ui.post("/api/scenarios/s03_model_heist/destroy", json={})


def test_language_switch_is_remembered(ui, state):
    assert ui.post("/api/lang", json={"lang": "zz"}).status_code == 400
    assert state.get_lang() is None
    assert ui.post("/api/lang", json={"lang": "TR"}).json() == {"lang": "tr"}
    assert state.get_lang() == "tr"
    turkish = ui.get("/api/overview").json()
    assert turkish["lang"] == "tr" and turkish["fallback"] is False
    assert turkish["strings"]["tab_flag"] != EN_UI["tab_flag"]
    detail = ui.get(f"/api/scenarios/{S00}").json()
    english_title = i18n.load_yaml(get_scenario(S00).path / "i18n.en.yml")["title"]
    assert detail["title"] != english_title and detail["fallback"] is False
    # Flags never depend on the language.
    flag = get_scenario(S00).flag(state)
    assert ui.post(f"/api/scenarios/{S00}/submit", json={"flag": flag}).json()["correct"] is True


# ---------------------------------------------------------------------- cli
def test_walkthrough_command_guards_spoilers(state):
    declined = invoke("walkthrough", S00, input="n\n")
    assert declined.exit_code == 1 and "Mitigation / Defense" not in declined.output
    forced = invoke("walkthrough", S00, "--yes")
    assert forced.exit_code == 0 and "Mitigation / Defense" in forced.output

    assert invoke("submit", S00, get_scenario(S00).flag(state)).exit_code == 0
    solved = invoke("walkthrough", "first_flag")
    assert solved.exit_code == 0 and "Mitigation / Defense" in solved.output


def test_walkthrough_lookup_falls_back_to_english():
    scenario = get_scenario(S00)
    path, fell_back = ops.walkthrough_path(scenario, "en")
    assert path is not None and path.name == "WALKTHROUGH.en.md" and fell_back is False
    path, fell_back = ops.walkthrough_path(scenario, "xx")
    assert path is not None and path.name == "WALKTHROUGH.en.md" and fell_back is True


def test_ui_command_reports_a_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        port = blocker.getsockname()[1]
        result = invoke("ui", "--port", str(port), "--no-browser")
    assert result.exit_code == 1 and str(port) in result.output


def test_ui_command_serves_the_page(isolated_home):
    """Start the real process, load the page and one API call, stop it again."""
    port = free_port()
    command = [sys.executable, "-m", "tensorgoat", "ui", "--port", str(port), "--no-browser"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    try:
        page = None
        for _ in range(100):
            try:
                page = httpx.get(url + "/", timeout=2)
                break
            except httpx.HTTPError:
                assert process.poll() is None, "the interface exited early"
                time.sleep(0.2)
        assert page is not None and page.status_code == 200
        token = re.search(r'TGOAT_TOKEN = "([^"]+)"', page.text).group(1)
        overview = httpx.get(url + "/api/overview", headers={"X-TGoat-Token": token}, timeout=5)
        assert overview.status_code == 200 and overview.json()["total"] == len(all_scenarios())
        assert httpx.get(url + "/api/overview", timeout=5).status_code == 403
    finally:
        process.kill()
        process.wait(timeout=10)
