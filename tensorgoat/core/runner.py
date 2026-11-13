"""Start and stop scenario services, natively (default) or with Docker.

Native mode launches ``python -m tensorgoat.core.serve`` as a background
process bound to ``127.0.0.1``. The process watches a token file; removing the
file asks it to shut down, so stopping a service never depends on signalling a
PID that the operating system may have recycled.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from tensorgoat.core.scenario import Scenario
from tensorgoat.core.state import HOME_ENV, State

BIND_HOST = "127.0.0.1"
TOKEN_FILE = "service.token"
LOG_FILE = "service.log"
COMPOSE_PROJECT = "tensorgoat"
DOCKER_DIR_ENV = "TENSORGOAT_DOCKER_DIR"

_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class RunnerError(Exception):
    """A start/stop failure; ``key`` names the catalogue message to show."""

    def __init__(self, key: str, **details: Any) -> None:
        super().__init__(key)
        self.key = key
        self.details = details


# ------------------------------------------------------------------- probing
def service_url(port: int) -> str:
    return f"http://{BIND_HOST}:{port}"


def probe(port: int, timeout: float = 1.0) -> dict[str, Any] | None:
    """``GET /`` on the local service; ``None`` when nothing (valid) answers."""
    try:
        with _NO_PROXY.open(service_url(port) + "/", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def port_is_free(port: int) -> bool:
    """True when nothing is listening on the local port.

    On POSIX a port that was just closed stays in TIME_WAIT for a while. A
    plain bind would then fail although no one listens (and although the
    server, which sets SO_REUSEADDR, could bind fine). Setting SO_REUSEADDR
    here makes the check agree with the server. On Windows the option means
    something else (it would allow binding to a port in use), so it is not set.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if os.name != "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((BIND_HOST, port))
        except OSError:
            return False
    return True


def _wait_until_port_is_free(port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_is_free(port):
            return True
        time.sleep(0.1)
    return port_is_free(port)


def is_running(scenario: Scenario, record: dict[str, Any]) -> bool:
    """True when the recorded port answers as this very scenario."""
    port = record.get("port")
    if not record.get("created") or not port:
        return False
    answer = probe(int(port))
    return bool(answer) and answer.get("scenario") == scenario.id


def _wait_until_ready(scenario: Scenario, port: int, timeout: float, proc: Any = None) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        answer = probe(port, timeout=0.5)
        if answer and answer.get("scenario") == scenario.id:
            return True
        time.sleep(0.15)
    return False


def _log_tail(path: Path, lines: int = 15) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


# -------------------------------------------------------------------- native
def native_command(scenario_id: str, port: int, lang: str, token_file: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "tensorgoat.core.serve",
        scenario_id,
        "--host",
        BIND_HOST,
        "--port",
        str(port),
        "--lang",
        lang,
        "--token-file",
        str(token_file),
    ]


def start_native(
    state: State, scenario: Scenario, port: int, lang: str, timeout: float = 45.0
) -> int:
    """Launch the service process and wait until it answers. Returns its PID."""
    if not port_is_free(port):
        raise RunnerError("errors.port_in_use", port=port)
    internal = state.internal_dir(scenario.id)
    internal.mkdir(parents=True, exist_ok=True)
    token_file = internal / TOKEN_FILE
    token_file.write_text(secrets.token_hex(8), encoding="utf-8")
    log_path = internal / LOG_FILE

    env = {**os.environ, HOME_ENV: str(state.home), "PYTHONUNBUFFERED": "1"}
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        options["start_new_session"] = True
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            native_command(scenario.id, port, lang, token_file),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            **options,
        )
    if not _wait_until_ready(scenario, port, timeout, proc):
        token_file.unlink(missing_ok=True)
        if proc.poll() is None:
            proc.kill()
        raise RunnerError("errors.service_failed", log=_log_tail(log_path), log_path=str(log_path))
    return proc.pid


def stop_native(state: State, scenario: Scenario, record: dict[str, Any]) -> None:
    """Ask the service to exit (token removal); kill it only as a last resort."""
    token_file = state.internal_dir(scenario.id) / TOKEN_FILE
    token_file.unlink(missing_ok=True)
    port = record.get("port")
    if not port:
        return
    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        answer = probe(int(port), timeout=0.3)
        if not answer or answer.get("scenario") != scenario.id:
            # It stopped answering; give the process a moment to release the port
            # so that an immediate restart on the same port succeeds.
            _wait_until_port_is_free(int(port), timeout=5.0)
            return
        time.sleep(0.15)
    # Still answering as our scenario: the recorded PID is the one serving it.
    pid = record.get("pid")
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass


# -------------------------------------------------------------------- docker
def docker_dir() -> Path | None:
    """Locate ``docker/compose.yml`` (repository checkout or explicit override)."""
    override = os.environ.get(DOCKER_DIR_ENV, "").strip()
    candidates = [Path(override)] if override else []
    candidates.append(Path(__file__).resolve().parents[2] / "docker")
    for candidate in candidates:
        if (candidate / "compose.yml").is_file():
            return candidate
    return None


def compose_command(directory: Path, *args: str) -> list[str]:
    compose_file = str(directory / "compose.yml")
    return ["docker", "compose", "-f", compose_file, "-p", COMPOSE_PROJECT, *args]


def _compose_env(state: State, lang: str) -> dict[str, str]:
    return {**os.environ, "TENSORGOAT_HOME_DIR": str(state.home), "TENSORGOAT_LANG": lang}


def start_docker(state: State, scenario: Scenario, lang: str, timeout: float = 600.0) -> None:
    directory = docker_dir()
    if directory is None:
        raise RunnerError("errors.docker_files_missing")
    if shutil.which("docker") is None:
        raise RunnerError("errors.docker_missing")
    command = compose_command(directory, "up", "-d", "--build", scenario.id)
    result = subprocess.run(
        command, env=_compose_env(state, lang), capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RunnerError("errors.docker_failed", log=result.stderr.strip()[-2000:])
    if not _wait_until_ready(scenario, int(scenario.port or 0), 60.0):
        raise RunnerError("errors.docker_failed", log="service did not become ready")


def stop_docker(state: State, scenario: Scenario) -> None:
    directory = docker_dir()
    if directory is None or shutil.which("docker") is None:
        return
    command = compose_command(directory, "rm", "--stop", "--force", scenario.id)
    subprocess.run(command, env=_compose_env(state, "en"), capture_output=True, timeout=120)


# ------------------------------------------------------------------ dispatch
def start(state: State, scenario: Scenario, *, port: int, lang: str, docker: bool) -> int | None:
    """Start a service in the requested mode; returns the PID in native mode."""
    if docker:
        start_docker(state, scenario, lang)
        return None
    return start_native(state, scenario, port, lang)


def stop(state: State, scenario: Scenario, record: dict[str, Any]) -> None:
    if record.get("mode") == "docker":
        stop_docker(state, scenario)
    elif record.get("mode") == "native":
        stop_native(state, scenario, record)
