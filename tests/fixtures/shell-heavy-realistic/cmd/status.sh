#!/usr/bin/env bash
# Show current application status and metrics summary.

set -e

source ../lib/common.sh
source ../lib/metrics.sh

PID_FILE="${PID_FILE:-/var/run/app.pid}"
APP_HOST="${APP_HOST:-localhost}"
APP_PORT="${APP_PORT:-8080}"

check_process_running() {
    if [ ! -f "${PID_FILE}" ]; then
        echo "status: stopped (no PID file)"
        return 1
    fi
    local pid
    pid=$(cat "${PID_FILE}")
    if kill -0 "${pid}" 2>/dev/null; then
        echo "status: running (pid=${pid})"
    else
        echo "status: stopped (stale PID file)"
        return 1
    fi
}

show_metrics_snapshot() {
    local snapshot
    snapshot=$(curl -s --max-time 5 \
        "http://${APP_HOST}:${APP_PORT}/metrics" 2>/dev/null) || {
        echo "metrics: unavailable"
        return 0
    }
    echo "metrics: available"
    echo "${snapshot}" | grep -E "^(app_|go_)" | head -10
}

check_process_running && show_metrics_snapshot || true
emit_counter "status_check"
