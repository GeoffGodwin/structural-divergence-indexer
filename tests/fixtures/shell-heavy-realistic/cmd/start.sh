#!/usr/bin/env bash
# Start the application service.

set -e

source ../lib/common.sh
source ../lib/config.sh

APP_PORT="${APP_PORT:-8080}"
PID_FILE="${PID_FILE:-/var/run/app.pid}"

log_info "Starting application on port ${APP_PORT}"

load_config || true

if [ -f "${PID_FILE}" ]; then
    existing_pid=$(cat "${PID_FILE}")
    if kill -0 "${existing_pid}" 2>/dev/null; then
        log_error "Application already running (pid=${existing_pid})"
        exit 1
    fi
    rm -f "${PID_FILE}"
fi

validate_config APP_PORT || true

start_app() {
    APP_PORT="${APP_PORT}" python -m app &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    log_info "Application started (pid=${pid})"
}

start_app
