#!/usr/bin/env bash
# End-to-end check in a clean environment.
#
#   fresh virtualenv -> pip install . -> tensorgoat list
#   -> for every scenario: create -> solve.py -> submit -> destroy
#
# Usage (from anywhere):  bash scripts/e2e_check.sh
#
# Environment:
#   PYTHON            interpreter used to create the virtualenv (default: python3, then python)
#   TENSORGOAT_SEED   optional seed for reproducible flags
#   E2E_KEEP=1        keep the temporary directory for inspection
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
fi

# Ask Python for the temp dir so the path is native on every platform.
WORK_DIR="$("$PYTHON" -c 'import tempfile; print(tempfile.mkdtemp(prefix="tgoat-e2e-"))')"
VENV_DIR="$WORK_DIR/venv"
export TENSORGOAT_HOME="$WORK_DIR/home"
unset TENSORGOAT_LANG || true

step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

cleanup() {
    status=$?
    if [ -x "${TGOAT:-}" ]; then
        "$TGOAT" destroy --all >/dev/null 2>&1 || true
    fi
    if [ "${E2E_KEEP:-0}" = "1" ]; then
        echo "kept: $WORK_DIR"
    else
        rm -rf "$WORK_DIR" || true
    fi
    if [ "$status" -eq 0 ]; then
        printf '\n\033[1;32mE2E CHECK PASSED\033[0m\n'
    else
        printf '\n\033[1;31mE2E CHECK FAILED (exit %s)\033[0m\n' "$status"
    fi
    exit "$status"
}
trap cleanup EXIT

step "Creating a clean virtual environment"
"$PYTHON" -m venv "$VENV_DIR"
if [ -d "$VENV_DIR/Scripts" ]; then BIN="$VENV_DIR/Scripts"; else BIN="$VENV_DIR/bin"; fi
VPY="$BIN/python"

step "pip install ."
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet .

TGOAT="$BIN/tensorgoat"
[ -x "$TGOAT" ] || TGOAT="$BIN/tensorgoat.exe"

step "tensorgoat list (and the tgoat alias)"
"$TGOAT" list
ALIAS="$BIN/tgoat"
[ -x "$ALIAS" ] || ALIAS="$BIN/tgoat.exe"
"$ALIAS" --version

# "<id> <type> <port>" for every scenario, straight from the installed package.
# Run from the work dir so the package under test is the installed one.
SCENARIOS="$(cd "$WORK_DIR" && "$VPY" -c '
from tensorgoat.scenarios import all_scenarios
for s in all_scenarios():
    print(s.id, s.type, s.port or 0)
')"

COUNT=0
while read -r ID TYPE PORT; do
    [ -n "$ID" ] || continue
    step "$ID ($TYPE)"
    "$TGOAT" create "$ID" >/dev/null
    WORKSPACE="$TENSORGOAT_HOME/workspace/$ID"
    if [ "$TYPE" = "service" ]; then
        OUTPUT="$("$VPY" "solutions/$ID/solve.py" --workspace "$WORKSPACE" --url "http://127.0.0.1:$PORT")"
    else
        OUTPUT="$("$VPY" "solutions/$ID/solve.py" --workspace "$WORKSPACE")"
    fi
    FLAG="$(printf '%s\n' "$OUTPUT" | tail -n 1 | tr -d '\r')"
    "$TGOAT" submit "$ID" "$FLAG"
    "$TGOAT" destroy "$ID"
    COUNT=$((COUNT + 1))
done <<EOF
$(printf '%s\n' "$SCENARIOS" | tr -d '\r')
EOF

step "Summary"
"$TGOAT" list
"$TGOAT" status
echo "scenarios solved end to end: $COUNT"
[ "$COUNT" -ge 7 ]
