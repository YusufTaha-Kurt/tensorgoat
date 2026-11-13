"""No real flag and no generated artefact may ever be committed."""

from __future__ import annotations

import subprocess
from pathlib import Path

from helpers import REPO_ROOT

from tensorgoat.core import flags
from tensorgoat.scenarios import all_scenarios

# Flag-shaped strings that are allowed in the repository: documentation examples
# and obviously fake test values. Their hex part must be one of these.
PLACEHOLDER_HEX = {"000000000000", "0123456789ab", "3fa9c01b7d22"}
ARTIFACT_SUFFIXES = {".pkl", ".pickle", ".safetensors", ".npz", ".npy", ".joblib"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "_parked"}
SKIP_DIRS |= {"build", "dist", "node_modules"}


def _repository_files() -> list[Path]:
    """Tracked and untracked-but-not-ignored files (falls back to a directory walk)."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=60,
            check=True,
        ).stdout.decode("utf-8")
        files = [REPO_ROOT / name for name in listing.split("\0") if name]
        if files:
            return [path for path in files if path.is_file()]
    except (OSError, subprocess.SubprocessError):
        pass
    return [
        path
        for path in REPO_ROOT.rglob("*")
        if path.is_file() and not (set(path.relative_to(REPO_ROOT).parts) & SKIP_DIRS)
    ]


def test_no_plaintext_flags_in_the_repository():
    files = _repository_files()
    assert len(files) > 50, "file discovery looks broken"
    known_real = set()
    for seed in ("ci", "pytest", "test", "seed", ""):
        secret = flags.derive_secret_from_seed(seed)
        known_real |= {flags.make_flag(secret, s.id, s.slug) for s in all_scenarios()}

    offenders = []
    for path in files:
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for found in flags.find_flags(text):
            hex_part = found[-13:-1]
            if hex_part not in PLACEHOLDER_HEX or found in known_real:
                offenders.append((path.relative_to(REPO_ROOT).as_posix(), found))
    assert not offenders, f"flag-shaped strings found: {offenders}"


def test_no_generated_artifacts_in_the_repository():
    committed = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in _repository_files()
        if path.suffix.lower() in ARTIFACT_SUFFIXES
    ]
    assert not committed, f"generated artefacts must not be committed: {committed}"


def test_gitignore_covers_artifacts_and_state():
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".tensorgoat/", "*.pkl", "*.safetensors", "*.npz", "*.npy", ".venv/"):
        assert pattern in ignored, pattern


def test_flag_placeholders_in_templates_are_not_flags():
    """Asset templates carry a placeholder, never a value."""
    for scenario in all_scenarios():
        assets = scenario.path / "assets"
        if not assets.is_dir():
            continue
        for path in assets.iterdir():
            assert not flags.find_flags(path.read_text(encoding="utf-8", errors="ignore"))
