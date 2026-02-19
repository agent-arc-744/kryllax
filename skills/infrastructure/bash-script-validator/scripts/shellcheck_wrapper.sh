#!/usr/bin/env bash
# shellcheck_wrapper.sh — Auto-install and run ShellCheck via Python venv
# Caches the venv so subsequent runs are fast
# Usage: bash shellcheck_wrapper.sh [--cache] [--clear-cache] <script.sh>

set -euo pipefail

CACHE_DIR="${HOME}/.cache/bash-script-validator"
VENV_DIR="${CACHE_DIR}/shellcheck-venv"
CLEAR_CACHE=false

for arg in "$@"; do
    case "$arg" in
        --clear-cache) CLEAR_CACHE=true ;;
    esac
done

if [[ "$CLEAR_CACHE" == true ]]; then
    rm -rf "$VENV_DIR"
    echo "Cache cleared: $VENV_DIR"
    exit 0
fi

# Create venv and install shellcheck-py if not cached
if [[ ! -f "${VENV_DIR}/bin/shellcheck" ]]; then
    echo "Installing shellcheck-py (one-time setup)..."
    mkdir -p "$CACHE_DIR"
    python3 -m venv "$VENV_DIR"
    "${VENV_DIR}/bin/pip" install --quiet shellcheck-py
    echo "✓ shellcheck-py installed and cached at $VENV_DIR"
fi

# Run shellcheck with remaining args (skip --cache flag)
args=()
for arg in "$@"; do
    [[ "$arg" != "--cache" ]] && args+=("$arg")
done

"${VENV_DIR}/bin/shellcheck" "${args[@]}"
