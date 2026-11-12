"""Helpers shared by the test modules."""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from typer.testing import CliRunner

from tensorgoat.core.flags import FLAG_PATTERN
from tensorgoat.core.state import State
from tensorgoat.scenarios import get_scenario

REPO_ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS = REPO_ROOT / "solutions"

# Run-time files of a live service; not part of the generated artefacts.
VOLATILE = {"service.log", "service.token"}

cli_runner = CliRunner()


def invoke(*args: str, input: str | None = None):
    """Run the CLI in-process (imports lazily so env fixtures apply first)."""
    from tensorgoat.cli import app

    return cli_runner.invoke(app, list(args), input=input)


def hash_tree(root: Path) -> dict[str, str]:
    """SHA-256 of every file below ``root`` (relative path -> digest)."""
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in VOLATILE:
            digests[path.relative_to(root).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return digests


def assert_deterministic(scenario_id: str, tmp_path: Path) -> None:
    """Generating twice with the same seed must give byte-identical artefacts."""
    scenario = get_scenario(scenario_id)
    hashes = []
    for name in ("first", "second"):
        state = State(tmp_path / name)
        scenario.generate(state)
        hashes.append(
            (
                hash_tree(state.workspace_dir(scenario.id)),
                hash_tree(state.internal_dir(scenario.id)),
            )
        )
    assert hashes[0] == hashes[1]
    assert hashes[0][0], "the scenario produced no workspace files"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_solve(scenario_id: str, workspace: Path, url: str | None = None) -> str:
    """Run ``solutions/<id>/solve.py`` as a player would; return the printed flag."""
    command = [sys.executable, str(SOLUTIONS / scenario_id / "solve.py"), "--workspace"]
    command.append(str(workspace))
    if url:
        command += ["--url", url]
    # The solver must not depend on TensorGoat's private state: hide it.
    env = {k: v for k, v in os.environ.items() if not k.startswith("TENSORGOAT_")}
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", env=env, timeout=120
    )
    assert result.returncode == 0, f"solve.py failed:\n{result.stdout}\n{result.stderr}"
    last_line = result.stdout.strip().splitlines()[-1]
    assert FLAG_PATTERN.fullmatch(last_line), f"last line is not a flag: {last_line!r}"
    return last_line


def assert_solvable(scenario_id: str, home: Path) -> None:
    """create -> solve.py -> submit -> destroy, exactly like a player."""
    scenario = get_scenario(scenario_id)
    state = State(home)
    args = ["create", scenario.id]
    port = None
    if scenario.is_service:
        port = free_port()
        args += ["--port", str(port)]
    started = time.monotonic()
    created = invoke(*args)
    assert created.exit_code == 0, created.output
    try:
        assert time.monotonic() - started < 60, "generation + service start took too long"
        url = f"http://127.0.0.1:{port}" if port else None
        flag = run_solve(scenario.id, state.workspace_dir(scenario.id), url)
        assert invoke("submit", scenario.id, "TGOAT{wrong_000000000000}").exit_code == 1
        accepted = invoke("submit", scenario.id, flag)
        assert accepted.exit_code == 0, accepted.output
        assert State(home).record(scenario.id)["solved"] is True
    finally:
        destroyed = invoke("destroy", scenario.id)
    assert destroyed.exit_code == 0, destroyed.output
    assert not state.workspace_dir(scenario.id).exists()


def assert_small_artifacts(scenario_id: str, state: State, limit_mb: float = 10.0) -> None:
    """No generated file (models included) may exceed the size budget."""
    for root in (state.workspace_dir(scenario_id), state.internal_dir(scenario_id)):
        for path in root.rglob("*"):
            if path.is_file():
                assert path.stat().st_size < limit_mb * 1024 * 1024, path
