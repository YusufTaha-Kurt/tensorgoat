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

step "Walkthroughs are part of the installed package"
ENGLISH="$("$TGOAT" walkthrough first_flag --yes)"
case "$ENGLISH" in *"Mitigation / Defense"*) ;; *) echo "English walkthrough not shown"; exit 1 ;; esac
TURKISH="$("$TGOAT" --lang tr walkthrough first_flag --yes)"
case "$TURKISH" in *"Savunma"*) ;; *) echo "Turkish walkthrough not shown"; exit 1 ;; esac
echo "walkthroughs: en, tr"

step "Web interface from the installed package"
UI_PORT="$("$VPY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])' | tr -d '\r')"
"$TGOAT" ui --no-browser --port "$UI_PORT" >/dev/null 2>&1 &
UI_PID=$!
(cd "$WORK_DIR" && "$VPY" - "$UI_PORT" <<'PY'
import json
import re
import sys
import time
import urllib.request

base = f"http://127.0.0.1:{sys.argv[1]}"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(100):
    try:
        page = opener.open(base + "/", timeout=2).read().decode("utf-8")
        break
    except OSError:
        time.sleep(0.2)
else:
    raise SystemExit("the web interface did not start")
token = re.search(r'TGOAT_TOKEN = "([^"]+)"', page).group(1)
for name in ("app.js", "style.css"):
    assert opener.open(f"{base}/static/{name}", timeout=5).status == 200, name
request = urllib.request.Request(base + "/api/overview", headers={"X-TGoat-Token": token})
overview = json.load(opener.open(request, timeout=5))
assert overview["total"] >= 8 and overview["solved"] == overview["total"], overview["solved"]
assert set(overview["languages"]) >= {"en", "tr"}
print(f"web interface: {overview['solved']} of {overview['total']} solved, languages {overview['languages']}")
PY
) || UI_FAILED=1
kill "$UI_PID" 2>/dev/null || true
wait "$UI_PID" 2>/dev/null || true
[ -z "${UI_FAILED:-}" ]

step "Summary"
"$TGOAT" list
"$TGOAT" status
echo "scenarios solved end to end: $COUNT"
[ "$COUNT" -ge 8 ]
