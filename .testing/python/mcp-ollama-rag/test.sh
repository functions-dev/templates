#!/bin/bash
#
# E2E test for python/mcp-ollama-rag
#
# Expects these vars from run-e2e.sh:
#   REPO_ROOT, LANGUAGE, TEMPLATE, FUNC_BIN, TEMPLATE_REPO, VERBOSE
#
# Prerequisites:
#   - ollama installed and running
#   - func CLI installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR=$(mktemp -d)
LISTEN_ADDRESS="${LISTEN_ADDRESS:-127.0.0.1:8080}"
RUN_PID=""

# stdout: verbose shows it, quiet sends to /dev/null
# stderr: always shown (errors always visible)
if [[ "$VERBOSE" == "true" ]]; then
    OUT=/dev/stdout
else
    OUT=/dev/null
fi

cleanup() {
    if [[ -n "$RUN_PID" ]] && ps -p "$RUN_PID" > /dev/null 2>&1; then
        kill "$RUN_PID" 2>/dev/null || true
        wait "$RUN_PID" 2>/dev/null || true
    fi
    lsof -ti ":${LISTEN_ADDRESS##*:}" 2>/dev/null | xargs kill 2>/dev/null || true
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

# ─── 1. Preflight ────────────────────────────────────────────
echo "[1/5] Preflight checks..."

if ! command -v ollama &>/dev/null; then
    echo "FAIL: ollama is not installed"
    exit 1
fi

if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
    echo "FAIL: ollama server not reachable at localhost:11434"
    echo "      Start it with: ollama serve"
    exit 1
fi

for model in "mxbai-embed-large" "llama3.2:3b"; do
    if ! ollama list 2>/dev/null | grep -q "$model"; then
        echo "  Pulling model: $model ..."
        ollama pull "$model" >"$OUT"
    else
        echo "  Model ready: $model"
    fi
done

echo "  OK"

# ─── 2. Create function from template ────────────────────────
echo "[2/5] Creating function from template..."

cd "$WORKDIR"
$FUNC_BIN create e2e-test -r "$TEMPLATE_REPO" -l "$LANGUAGE" -t "$TEMPLATE" >"$OUT"
cd e2e-test

echo "  OK"

# ─── 3. Install test client deps ─────────────────────────────
echo "[3/5] Installing test client dependencies..."

python -m venv "$WORKDIR/.venv" >"$OUT"
source "$WORKDIR/.venv/bin/activate"
pip install mcp httpx >"$OUT"

echo "  OK"

# ─── 4. Start function server ────────────────────────────────
echo "[4/5] Starting function server..."

if lsof -ti ":${LISTEN_ADDRESS##*:}" &>/dev/null; then
    echo "FAIL: Port ${LISTEN_ADDRESS##*:} is already in use"
    exit 1
fi

LISTEN_ADDRESS="$LISTEN_ADDRESS" $FUNC_BIN run --builder=host >"$OUT" &
RUN_PID=$!

for i in $(seq 1 30); do
    if curl -sf "http://$LISTEN_ADDRESS/" &>/dev/null; then
        break
    fi
    if ! ps -p "$RUN_PID" > /dev/null 2>&1; then
        echo "FAIL: func run process died"
        exit 1
    fi
    sleep 2
done

if ! curl -sf "http://$LISTEN_ADDRESS/" &>/dev/null; then
    echo "FAIL: Server did not start within 60s"
    exit 1
fi

echo "  OK"

# ─── 5. Run MCP client tests ─────────────────────────────────
echo "[5/5] Running MCP client tests..."

python "$SCRIPT_DIR/test_mcp_client.py" "http://$LISTEN_ADDRESS/mcp" >"$OUT"

echo "  OK"
echo ""
echo "=== PASS ==="
