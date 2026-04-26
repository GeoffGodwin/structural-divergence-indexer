#!/usr/bin/env bash
# Structured logging primitives.

log_info()  { printf '[INFO]  %s\n' "$*"; }
log_warn()  { printf '[WARN]  %s\n' "$*" >&2; }
log_error() { printf '[ERROR] %s\n' "$*" >&2; }
log_debug() {
    [[ "${LOG_LEVEL:-INFO}" == "DEBUG" ]] && printf '[DEBUG] %s\n' "$*" >&2 || true
}
