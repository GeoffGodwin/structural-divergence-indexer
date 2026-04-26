#!/usr/bin/env bash
# Core shared utilities.
# Sources log.sh and util (extensionless — exercises M15 extension fallback).
# "source ./util" resolves to lib/util via the shell adapter, which the graph
# builder then resolves to lib/util.sh via the .sh extension fallback.

source ./log.sh
source ./util

say() { log_info "$*"; }

require_env() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        log_error "Required env var not set: ${name}"
        exit 1
    fi
}
