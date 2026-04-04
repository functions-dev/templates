# E2E Testing Framework

End-to-end tests for templates that need external services (Ollama, databases, etc.)
and can't be tested with a simple `func invoke`.

## Usage

```bash
# Run all e2e tests
make e2e

# Run a specific test
make e2e ARGS="python/mcp-ollama-rag"

# Verbose output
make e2e ARGS="--verbose"

# Or run directly
./.testing/run-e2e.sh python/mcp-ollama-rag --verbose
```

## Structure

```
.testing/
  run-e2e.sh                              # runner script
  README.md
  <language>/
    <template>/                           # must match a template in the repo
      test.sh                             # entry point (required)
      test_mcp_client.py                  # helper scripts (optional)
```

## Adding a new e2e test

1. Create `.testing/<language>/<template>/test.sh`
2. The directory name **must** match an existing template (e.g. `python/mcp-ollama-rag`)
3. The runner discovers it automatically

## Writing test.sh

Each `test.sh` is self-contained. It receives these environment variables
from `run-e2e.sh`:

| Variable | Description |
|---|---|
| `REPO_ROOT` | Absolute path to the repo root |
| `LANGUAGE` | Template language (e.g. `python`) |
| `TEMPLATE` | Template name (e.g. `mcp-ollama-rag`) |
| `FUNC_BIN` | Path to `func` binary |
| `TEMPLATE_REPO` | Git URI or `file://` path to the templates repo |
| `VERBOSE` | `true` or `false` |

### Conventions

- Use `set -euo pipefail` — fail fast on errors.
- Use a temp directory for `func create` and clean up via `trap cleanup EXIT`.
- Redirect stdout with `>"$OUT"` where `OUT` is `/dev/stdout` (verbose) or `/dev/null` (quiet). stderr always prints so errors are always visible.
- Print step progress: `echo "[1/N] Step name..."` and `echo "  OK"`.
- Exit 0 on success, non-zero on failure.
- Print `=== PASS ===` at the end on success.

### Example

```bash
#!/bin/bash
set -euo pipefail

WORKDIR=$(mktemp -d)
if [[ "$VERBOSE" == "true" ]]; then OUT=/dev/stdout; else OUT=/dev/null; fi
trap "rm -rf $WORKDIR" EXIT

echo "[1/3] Creating function..."
cd "$WORKDIR"
$FUNC_BIN create test -r "$TEMPLATE_REPO" -l "$LANGUAGE" -t "$TEMPLATE" >"$OUT"
cd test
echo "  OK"

echo "[2/3] Starting server..."
$FUNC_BIN run --builder=host >"$OUT" &
RUN_PID=$!
trap "kill $RUN_PID 2>/dev/null; rm -rf $WORKDIR" EXIT
sleep 10
echo "  OK"

echo "[3/3] Testing..."
curl -sf http://localhost:8080/ >"$OUT"
echo "  OK"

echo "=== PASS ==="
```

## Future improvements

- Extract common helpers (step counter, verbose redirection, cleanup) into a
  `common.sh` once there are 2-3 tests sharing the same patterns.

## CI

The `e2e-tests.yaml` workflow runs automatically on PRs when template files or
test files change. Each test runs in a separate parallel job. Manual trigger
via `workflow_dispatch` runs all tests.
