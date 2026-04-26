#!/usr/bin/env bash
# Structured logging utilities.

LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_FILE="${LOG_FILE:-}"

_log() {
    local level="$1"
    shift
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf "[%s] [%s] %s\n" "${ts}" "${level}" "$*"
}

log_debug() {
    [ "${LOG_LEVEL}" = "debug" ] || return 0
    _log "DEBUG" "$@"
}

log_info() {
    _log "INFO" "$@"
}

log_warn() {
    _log "WARN" "$@" >&2
}

log_error() {
    _log "ERROR" "$@" >&2
}

log_to_file() {
    local msg="$1"
    if [ -n "${LOG_FILE}" ]; then
        echo "${msg}" >> "${LOG_FILE}"
    fi
    logger -t "app" "${msg}"
}

audit_log() {
    local action="$1"
    local target="$2"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '{"ts":"%s","action":"%s","target":"%s"}\n' "${ts}" "${action}" "${target}"
}
