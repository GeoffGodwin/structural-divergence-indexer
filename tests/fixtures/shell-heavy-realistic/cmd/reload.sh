#!/usr/bin/env bash
# Reload application configuration without full restart.

set -e

source ../lib/common.sh
source ../lib/config.sh
source ../lib/logging.sh

PID_FILE="${PID_FILE:-/var/run/app.pid}"

log_info "Reloading application configuration"

if [ ! -f "${PID_FILE}" ]; then
    log_error "Application not running (no PID file)"
    exit 1
fi

pid=$(cat "${PID_FILE}")

if ! kill -0 "${pid}" 2>/dev/null; then
    log_error "Application process ${pid} not running"
    exit 1
fi

load_config || { log_warn "Could not reload config file; keeping current config"; }
validate_config APP_PORT APP_HOST || log_warn "Some config keys missing after reload"

log_info "Sending SIGHUP to pid=${pid}"
kill -HUP "${pid}" || { log_error "Failed to send SIGHUP to ${pid}"; exit 1; }

sleep 2
if kill -0 "${pid}" 2>/dev/null; then
    log_info "Application reloaded successfully (pid=${pid})"
else
    log_error "Application exited after reload signal"
    exit 1
fi
