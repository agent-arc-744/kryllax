#!/usr/bin/env bash
# bash-script-validator — Main validation script
# Part of the Kryllax bash-script-validator skill
# Usage: bash validate.sh <script.sh>

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

error_count=0
warn_count=0
info_count=0

print_header() {
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}   BASH/SHELL SCRIPT VALIDATOR${NC}"
    echo -e "${BOLD}========================================${NC}"
}

print_section() {
    echo -e "\n${CYAN}[${1}]${NC}"
}

print_ok()   { echo -e "${GREEN}✓${NC} $*"; }
print_warn() { echo -e "${YELLOW}⚠${NC} $*"; ((warn_count++)) || true; }
print_err()  { echo -e "${RED}✗${NC} $*"; ((error_count++)) || true; }
print_info() { echo -e "  ℹ $*"; ((info_count++)) || true; }

detect_shell() {
    local file="$1"
    local shebang
    shebang=$(head -1 "$file" 2>/dev/null || echo "")
    case "$shebang" in
        *"/bash"*|*"env bash"*)  echo "bash" ;;
        *"/zsh"*|*"env zsh"*)   echo "zsh" ;;
        *"/ksh"*|*"env ksh"*)   echo "ksh" ;;
        *"/dash"*|*"env dash"*) echo "dash" ;;
        *"/sh"*|*"env sh"*)     echo "sh" ;;
        *)                       echo "bash" ;; # default
    esac
}

check_syntax() {
    local file="$1" shell="$2"
    print_section "SYNTAX CHECK"
    local output
    if output=$("$shell" -n "$file" 2>&1); then
        print_ok "No syntax errors found ($shell -n)"
    else
        print_err "Syntax error detected:"
        echo "$output" | sed 's/^/    /'
    fi
}

check_shellcheck() {
    local file="$1" shell="$2"
    print_section "SHELLCHECK"

    local sc_bin=""
    if command -v shellcheck &>/dev/null; then
        sc_bin="shellcheck"
    elif command -v shellcheck-py &>/dev/null; then
        sc_bin="shellcheck-py"
    fi

    if [[ -z "$sc_bin" ]]; then
        print_info "ShellCheck not installed. Install: apt-get install shellcheck"
        print_info "Or use the wrapper: bash scripts/shellcheck_wrapper.sh $file"
        return
    fi

    local output
    if output=$("$sc_bin" -s "$shell" -f gcc "$file" 2>&1); then
        print_ok "ShellCheck: no issues found"
    else
        echo "$output" | while IFS= read -r line; do
            if [[ "$line" == *"error"* ]]; then
                echo -e "  ${RED}$line${NC}"
                ((error_count++)) || true
            elif [[ "$line" == *"warning"* ]]; then
                echo -e "  ${YELLOW}$line${NC}"
                ((warn_count++)) || true
            else
                echo "  $line"
                ((info_count++)) || true
            fi
        done
    fi
}

check_security() {
    local file="$1" shell="$2"
    print_section "SECURITY CHECKS"
    local found=0

    # eval with variable
    if grep -n 'eval [^"'\''$]\|eval $' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
        print_err "Unsafe eval with variable (command injection risk)"
        grep -n 'eval ' "$file" | grep -v '^[[:space:]]*#' | sed 's/^/    Line /'
        found=1
    fi

    # rm -rf with variable or *
    if grep -n 'rm -rf \*\|rm -rf \$' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
        print_err "Dangerous rm -rf pattern detected"
        grep -n 'rm -rf' "$file" | grep -v '^[[:space:]]*#' | sed 's/^/    Line /'
        found=1
    fi

    # Unquoted $@ or $*
    if grep -n '[^"$]\$@\|[^"$]\$\*' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
        print_warn "Unquoted \$@ or \$* — use \"\$@\" to preserve arguments"
        found=1
    fi

    # Backticks
    if grep -n '`' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
        print_warn "Backtick command substitution — prefer \$()"
        grep -n '`' "$file" | grep -v '^[[:space:]]*#' | head -3 | sed 's/^/    Line /'
        found=1
    fi

    # Useless use of cat
    if grep -n 'cat .* | ' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
        print_info "Useless use of cat (UUOC) — pipe directly or use redirection"
        grep -n 'cat .* | ' "$file" | grep -v '^[[:space:]]*#' | head -3 | sed 's/^/    Line /'
        found=1
    fi

    # Missing set -e / set -euo pipefail for bash
    if [[ "$shell" == "bash" ]]; then
        if ! grep -q 'set -.*e\|set -euo\|set -eu' "$file" 2>/dev/null; then
            print_warn "Missing 'set -euo pipefail' — script won't exit on errors"
            found=1
        fi
    fi

    # Bashisms in sh scripts
    if [[ "$shell" == "sh" || "$shell" == "dash" ]]; then
        if grep -n '\[\[\|\]\]' "$file" 2>/dev/null | grep -v '^[[:space:]]*#'; then
            print_err "Bashism [[ ]] in POSIX sh script — use [ ] instead"
            found=1
        fi
        if grep -n 'local ' "$file" 2>/dev/null | grep -v '^[[:space:]]*#' | grep -v 'function\|()'; then
            print_warn "'local' is not POSIX — may not work in all sh implementations"
            found=1
        fi
    fi

    [[ $found -eq 0 ]] && print_ok "No security issues detected"
}

print_summary() {
    local file="$1"
    echo -e "\n${BOLD}========================================${NC}"
    echo -e "${BOLD}VALIDATION SUMMARY${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "File:     $file"
    echo -e "Errors:   ${RED}${error_count}${NC}"
    echo -e "Warnings: ${YELLOW}${warn_count}${NC}"
    echo -e "Info:     ${info_count}"

    if [[ $error_count -gt 0 ]]; then
        echo -e "\n${RED}${BOLD}RESULT: FAILED${NC}"
        return 2
    elif [[ $warn_count -gt 0 ]]; then
        echo -e "\n${YELLOW}${BOLD}RESULT: WARNINGS${NC}"
        return 1
    else
        echo -e "\n${GREEN}${BOLD}RESULT: CLEAN${NC}"
        return 0
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 <script.sh> [script2.sh ...]"
        exit 1
    fi

    for file in "$@"; do
        if [[ ! -f "$file" ]]; then
            echo -e "${RED}Error: File not found: $file${NC}" >&2
            exit 1
        fi

        print_header
        echo -e "File:  ${BOLD}$file${NC}"
        local shell
        shell=$(detect_shell "$file")
        echo -e "Shell: ${BOLD}$shell${NC}"

        check_syntax "$file" "$shell"
        check_shellcheck "$file" "$shell"
        check_security "$file" "$shell"
        print_summary "$file"
    done
}

main "$@"
