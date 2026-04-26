#!/usr/bin/env bash
# Common utilities shared across all scripts.

set -e

log_info() {
    echo "[INFO] $*"
}

log_warn() {
    echo "[WARN] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

die() {
    log_error "$1"
    exit 1
}

require_var() {
    local name="$1"
    local val="${2:-}"
    if [ -z "${val}" ]; then
        log_error "Required variable not set: ${name}"
        exit 1
    fi
}

check_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        die "Required command not found: ${cmd}"
    fi
}

timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}
