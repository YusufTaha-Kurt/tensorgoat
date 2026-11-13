"""Safety rules that hold for the whole project (design principles 1-6)."""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest
import yaml
from helpers import REPO_ROOT, free_port

from tensorgoat.core import runner, serve
from tensorgoat.core.state import State
from tensorgoat.scenarios import all_scenarios, get_scenario

PACKAGE = REPO_ROOT / "tensorgoat"
SERVICES = [scenario for scenario in all_scenarios() if scenario.is_service]

# Modules allowed to start processes / open sockets / talk HTTP: only the runner
# (and only towards 127.0.0.1).
PROCESS_MODULES = {"tensorgoat/core/runner.py"}
FORBIDDEN_IMPORTS = {"torch", "tensorflow", "keras", "jax", "requests", "pickle", "dill", "marshal"}
FORBIDDEN_IMPORTS |= {"cloudpickle", "joblib", "shelve", "ftplib", "smtplib", "telnetlib"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _package_sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def test_services_bind_to_localhost_only():
    assert runner.BIND_HOST == "127.0.0.1"
    assert serve.DEFAULT_HOST == "127.0.0.1"
    for scenario in SERVICES:
        command = runner.native_command(scenario.id, int(scenario.port), "en", Path("token"))
        assert command[command.index("--host") + 1] == "127.0.0.1"
        assert runner.service_url(int(scenario.port)).startswith("http://127.0.0.1:")


def test_docker_ports_are_published_on_localhost_only():
    compose = yaml.safe_load((REPO_ROOT / "docker" / "compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert set(services) == {scenario.id for scenario in SERVICES}
    for scenario in SERVICES:
        ports = services[scenario.id]["ports"]
        assert ports == [f"127.0.0.1:{scenario.port}:{scenario.port}"]
        command = services[scenario.id]["command"]
        assert command[0] == scenario.id and str(scenario.port) in command
        volumes = services[scenario.id]["volumes"]
        assert all(str(volume).endswith(":ro") for volume in volumes), "mount the state read-only"
        assert services[scenario.id]["user"].startswith("${TENSORGOAT_UID:-10001}:")


def test_docker_runs_as_the_host_user_where_that_exists(state, monkeypatch):
    """The container must be able to read a state directory only its owner can read."""
    import os

    monkeypatch.delenv("TENSORGOAT_UID", raising=False)
    monkeypatch.delenv("TENSORGOAT_GID", raising=False)
    env = runner._compose_env(state, "en")
    assert env["TENSORGOAT_HOME_DIR"] == str(state.home) and env["TENSORGOAT_LANG"] == "en"
    if hasattr(os, "getuid"):
        assert env["TENSORGOAT_UID"] == str(os.getuid())
        assert env["TENSORGOAT_GID"] == str(os.getgid())
    else:
        assert "TENSORGOAT_UID" not in env, "Windows keeps the image's unprivileged user"


def _non_loopback_addresses() -> list[str]:
    """IPv4 addresses of this machine other than 127.x (best effort, sends nothing)."""
    addresses: set[str] = set()
    try:
        addresses |= {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None)}
    except OSError:
        pass
    # On many Linux hosts the host name resolves to 127.0.1.1 only. Connecting a
    # UDP socket transmits no packet but reveals the address of the default route.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 9))
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    return sorted(a for a in addresses if ":" not in a and not a.startswith(("127.", "0.")))


def test_running_service_is_not_reachable_from_other_interfaces(isolated_home):
    """Start one real service and try to reach it through a non-loopback address."""
    external = _non_loopback_addresses()
    if not external:
        pytest.skip("this machine has no non-loopback IPv4 address")

    scenario = get_scenario("s03_model_heist")
    state = State(isolated_home)
    scenario.generate(state)
    port = free_port()
    runner.start_native(state, scenario, port, "en")
    try:
        assert runner.probe(port)["scenario"] == scenario.id
        for address in external:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.5)
                assert sock.connect_ex((address, port)) != 0, f"reachable via {address}"
    finally:
        runner.stop_native(state, scenario, {"port": port, "pid": None})


def test_no_heavy_or_unsafe_dependencies():
    """numpy/scikit-learn only: no deep-learning frameworks, no pickle, no HTTP clients."""
    for path in _package_sources():
        relative = path.relative_to(REPO_ROOT).as_posix()
        imported = _imports(ast.parse(path.read_text(encoding="utf-8")))
        assert not (imported & FORBIDDEN_IMPORTS), f"{relative} imports {imported}"
        if relative not in PROCESS_MODULES:
            for module in ("subprocess", "socket", "urllib", "httpx", "http"):
                assert module not in imported, f"{relative} must not import {module}"


def test_no_dynamic_code_execution_or_shell_calls():
    for path in _package_sources():
        relative = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                assert node.func.id not in FORBIDDEN_CALLS, f"{relative}:{node.lineno}"
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"system", "popen"}, f"{relative}:{node.lineno}"
            for keyword in node.keywords:
                if keyword.arg == "shell":
                    assert not (isinstance(keyword.value, ast.Constant) and keyword.value.value), (
                        f"{relative}:{node.lineno} uses shell=True"
                    )


def test_runner_only_talks_to_localhost():
    source = (PACKAGE / "core" / "runner.py").read_text(encoding="utf-8")
    assert "0.0.0.0" not in source
    assert "ProxyHandler({})" in source, "health checks must bypass system proxies"


def test_pickle_is_only_written_never_loaded_by_the_package():
    """S02 assembles bytes by hand; nothing in the package unpickles anything."""
    for path in _package_sources():
        source = path.read_text(encoding="utf-8")
        assert "pickle.load" not in source and "allow_pickle=True" not in source, path.name


def test_port_check_detects_listeners_and_recovers_after_close():
    """Regression: a just-closed port (TIME_WAIT on Linux) must count as free again."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        assert runner.port_is_free(port) is False
        # Open and close a connection so the port has recent traffic.
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            accepted, _ = server.accept()
            client.sendall(b"x")
            accepted.recv(1)
            accepted.close()
    assert runner._wait_until_port_is_free(port, timeout=5.0) is True
