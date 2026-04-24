#!/usr/bin/env bash

log_info() {
    echo "[INFO] $*"
}

log_error() {
    echo "[ERROR] $*" >&2
}

check_dependency() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Required command not found: ${cmd}" >&2
        exit 1
    fi
}

require_var() {
    local name="$1"
    local val="${2:-}"
    if [ -z "${val}" ]; then
        log_error "Required variable not set: ${name}"
        exit 1
    fi
}
