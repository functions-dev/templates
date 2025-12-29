#!/bin/bash
#
# invoke-local.sh - Test all function templates locally
#
# This script replicates the invoke-all.yaml GitHub workflow for local testing.
# It discovers all language/template combinations, builds, runs, and invokes each one.
#
# Usage: ./invoke-local.sh
#
# Environment variables:
#   FUNC_BIN      - Path to func binary (default: func)
#   FUNC_REGISTRY - Container registry to use (default: quay.io/test)
#
# Requirements:
#   - func CLI installed
#   - hugo (for go/blog template)
#   - npm (for typescript templates)
#   - cargo (for rust templates)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR=$(mktemp -d)
HOST_ENABLED_LANGUAGES=("go" "python")
REGISTRY="${FUNC_REGISTRY:-quay.io/test}"
FUNC_BIN="${FUNC_BIN:-func}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
declare -a PASSED=()
declare -a FAILED=()
declare -a FAILED_DIRS=()

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup_on_success() {
    local dir=$1
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        log_info "Cleaned up: $dir"
    fi
}

is_host_enabled() {
    local lang=$1
    for enabled in "${HOST_ENABLED_LANGUAGES[@]}"; do
        if [[ "$lang" == "$enabled" ]]; then
            return 0
        fi
    done
    return 1
}

run_prerequisites() {
    local language=$1
    local template=$2

    log_info "Running prerequisites for $language/$template"

    case "$language/$template" in
        go/blog)
            log_info "Building hugo static files"
            make
            ;;
        typescript/*)
            log_info "Running npm install"
            npm install
            ;;
        rust/*)
            log_info "Running cargo build"
            cargo build
            ;;
        *)
            log_info "No prerequisites needed"
            ;;
    esac
}

test_template() {
    local language=$1
    local template=$2
    local func_name="$language-$template"
    local func_dir="$WORKDIR/$func_name"
    local run_pid=""

    log_info "=========================================="
    log_info "Testing: $language/$template"
    log_info "=========================================="

    # Determine builder
    local builder="pack"
    if is_host_enabled "$language"; then
        builder="host"
    fi
    log_info "Using builder: $builder"

    # Create function using func create with local repository (file:// protocol)
    local repo_uri="file://$SCRIPT_DIR"
    log_info "Creating function with: $FUNC_BIN create $func_name -r $repo_uri -l $language -t $template"
    cd "$WORKDIR"

    if ! $FUNC_BIN create "$func_name" -r "$repo_uri" -l "$language" -t "$template"; then
        log_error "func create failed for $language/$template"
        return 1
    fi

    cd "$func_dir"

    if [[ ! -f "func.yaml" ]]; then
        log_error "No func.yaml found after func create"
        return 1
    fi

    # Run prerequisites
    run_prerequisites "$language" "$template"

    # Build
    log_info "Building function"
    if ! FUNC_REGISTRY="$REGISTRY" $FUNC_BIN build --builder="$builder"; then
        log_error "Build failed for $language/$template"
        return 1
    fi

    # Run in background
    log_info "Starting function"
    $FUNC_BIN run --build=false &
    run_pid=$!

    # Check if process started
    sleep 2
    if ! ps -p $run_pid > /dev/null 2>&1; then
        log_error "Failed to start function"
        return 1
    fi

    # Wait for function to be ready
    log_info "Waiting for function to be ready..."
    sleep 10

    # Invoke with retries
    local max_retries=5
    local retry_count=0
    local success=false

    while [[ $retry_count -lt $max_retries ]]; do
        log_info "Invoke attempt $((retry_count + 1)) of $max_retries"
        if $FUNC_BIN invoke --request-type=GET 2>/dev/null; then
            log_info "Invoke succeeded!"
            success=true
            break
        else
            log_warn "Invoke failed, retrying..."
            retry_count=$((retry_count + 1))
            sleep 5
        fi
    done

    # Cleanup: kill the running function
    if [[ -n "$run_pid" ]] && ps -p $run_pid > /dev/null 2>&1; then
        kill $run_pid 2>/dev/null || true
        wait $run_pid 2>/dev/null || true
    fi

    if [[ "$success" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "                SUMMARY"
    echo "=========================================="
    echo ""

    if [[ ${#PASSED[@]} -gt 0 ]]; then
        echo -e "${GREEN}PASSED (${#PASSED[@]}):${NC}"
        for item in "${PASSED[@]}"; do
            echo "  - $item"
        done
    fi

    echo ""

    if [[ ${#FAILED[@]} -gt 0 ]]; then
        echo -e "${RED}FAILED (${#FAILED[@]}):${NC}"
        for i in "${!FAILED[@]}"; do
            echo "  - ${FAILED[$i]}"
            echo "    Preserved at: ${FAILED_DIRS[$i]}"
        done
    fi

    echo ""
    echo "Total: $((${#PASSED[@]} + ${#FAILED[@]})) | Passed: ${#PASSED[@]} | Failed: ${#FAILED[@]}"

    if [[ ${#FAILED[@]} -gt 0 ]]; then
        return 1
    fi
    return 0
}

main() {
    log_info "Starting local template testing"
    log_info "Script directory: $SCRIPT_DIR"
    log_info "Work directory: $WORKDIR"
    echo ""

    # Find all language directories
    for lang_dir in "$SCRIPT_DIR"/*/; do
        # Skip hidden directories and non-directories
        [[ ! -d "$lang_dir" ]] && continue
        [[ "$(basename "$lang_dir")" == .* ]] && continue

        local language=$(basename "$lang_dir")

        # Skip non-language directories
        if [[ "$language" == "docs" ]] || [[ "$language" == ".github" ]]; then
            continue
        fi

        # Find all templates in this language
        for template_dir in "$lang_dir"/*/; do
            [[ ! -d "$template_dir" ]] && continue

            local template=$(basename "$template_dir")
            local test_name="$language/$template"
            local func_dir="$WORKDIR/$language-$template"

            if test_template "$language" "$template"; then
                PASSED+=("$test_name")
                cleanup_on_success "$func_dir"
            else
                FAILED+=("$test_name")
                FAILED_DIRS+=("$func_dir")
                log_error "FAILED: $test_name (preserved at $func_dir)"
            fi

            echo ""
        done
    done

    print_summary
}

# Run main
main "$@"
