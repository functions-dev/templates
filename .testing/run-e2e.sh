#!/bin/bash
#
# run-e2e.sh — Run e2e tests for templates
#
# Usage:
#   ./.testing/run-e2e.sh                              # run all e2e tests
#   ./.testing/run-e2e.sh python/mcp-ollama-rag        # run one test
#   ./.testing/run-e2e.sh --verbose                    # run all, verbose
#   ./.testing/run-e2e.sh python/mcp-ollama-rag --verbose
#
# Each test is a self-contained test.sh in .testing/<language>/<template>/.
#
# Options:
#   --verbose  Show all stdout from test commands (stderr always shown)
#
# Environment variables:
#   FUNC_BIN       - Path to func binary (default: func)
#   TEMPLATE_REPO  - Git URI or file:// path to templates repo (default: file://<repo-root>)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBOSE=false

# Parse args
TARGETS=()
for arg in "$@"; do
    case "$arg" in
        --verbose) VERBOSE=true ;;
        -*) echo "Unknown flag: $arg"; exit 1 ;;
        *) TARGETS+=("${arg%/}") ;;
    esac
done

export REPO_ROOT
export VERBOSE
export FUNC_BIN="${FUNC_BIN:-func}"
export TEMPLATE_REPO="${TEMPLATE_REPO:-file://$REPO_ROOT}"

# Discover all available tests
discover_tests() {
    find "$SCRIPT_DIR" -mindepth 3 -maxdepth 3 -name "test.sh" | sort | while read -r f; do
        rel="${f#$SCRIPT_DIR/}"
        dirname "$rel"
    done
}

# If no targets, run all
if [[ ${#TARGETS[@]} -eq 0 ]]; then
    while IFS= read -r t; do
        TARGETS+=("$t")
    done < <(discover_tests)
fi

if [[ ${#TARGETS[@]} -eq 0 ]]; then
    echo "No e2e tests found in $SCRIPT_DIR"
    exit 0
fi

# Run tests and collect results
PASSED=()
FAILED=()
TOTAL_START=$(date +%s)

for target in "${TARGETS[@]}"; do
    LANGUAGE="${target%%/*}"
    TEMPLATE="${target#*/}"

    export LANGUAGE
    export TEMPLATE

    # Validate template exists in repo
    if [[ ! -d "$REPO_ROOT/$LANGUAGE/$TEMPLATE" ]]; then
        echo "ERROR: Template not found: $LANGUAGE/$TEMPLATE"
        echo "  Expected: $REPO_ROOT/$LANGUAGE/$TEMPLATE"
        FAILED+=("$target")
        continue
    fi

    # Validate test exists
    TEST_SCRIPT="$SCRIPT_DIR/$LANGUAGE/$TEMPLATE/test.sh"
    if [[ ! -f "$TEST_SCRIPT" ]]; then
        echo "ERROR: No test.sh found for $target"
        FAILED+=("$target")
        continue
    fi

    echo "=== $target ==="
    START=$(date +%s)

    if bash "$TEST_SCRIPT"; then
        ELAPSED=$(( $(date +%s) - START ))
        PASSED+=("$target (${ELAPSED}s)")
    else
        ELAPSED=$(( $(date +%s) - START ))
        FAILED+=("$target (${ELAPSED}s)")
    fi
    echo ""
done

# Summary
TOTAL_ELAPSED=$(( $(date +%s) - TOTAL_START ))
echo "=== E2E Summary ==="
for p in "${PASSED[@]}"; do
    printf "\033[32mPASS\033[0m %s\n" "$p"
done
for f in "${FAILED[@]}"; do
    printf "\033[31mFAIL\033[0m %s\n" "$f"
done
echo ""
echo "${#PASSED[@]} passed, ${#FAILED[@]} failed in ${TOTAL_ELAPSED}s"

if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
