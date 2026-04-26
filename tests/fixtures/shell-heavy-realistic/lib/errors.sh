#!/usr/bin/env bash
# Error handling patterns and utilities.

set -euo pipefail

ERR_FILE=""

setup_error_trap() {
    local handler="${1:-_default_err_handler}"
    trap "${handler}" ERR
}

_default_err_handler() {
    local exit_code=$?
    echo "[ERROR] Command failed with exit code ${exit_code}" >&2
    exit "${exit_code}"
}

trap_with_context() {
    trap 'log_error "Unexpected error at line $LINENO"; exit 1' ERR EXIT
}

assert_success() {
    local cmd="$1"
    if ! eval "${cmd}"; then
        echo "[ASSERT] Command failed: ${cmd}" >&2
        exit 2
    fi
}

retry() {
    local attempts="$1"
    local delay="$2"
    shift 2
    local i=0
    while [ "${i}" -lt "${attempts}" ]; do
        "$@" && return 0
        i=$(( i + 1 ))
        sleep "${delay}"
    done
    return 1
}

fail_unless() {
    local condition="$1"
    local message="${2:-Assertion failed}"
    if ! eval "${condition}"; then
        echo "[FAIL] ${message}" >&2
        exit 1
    fi
}
