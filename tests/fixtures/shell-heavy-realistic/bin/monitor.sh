#!/usr/bin/env bash
# Monitor application health and emit metrics.

set -e

source ../lib/common.sh
source ../lib/logging.sh
source ../lib/metrics.sh

INTERVAL="${INTERVAL:-60}"
APP_HOST="${APP_HOST:-localhost}"
APP_PORT="${APP_PORT:-8080}"

log_info "Starting monitor: host=${APP_HOST} port=${APP_PORT} interval=${INTERVAL}s"

check_cmd curl

collect_metrics() {
    local start_ns
    start_ns=$(date +%s%N)

    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 "http://${APP_HOST}:${APP_PORT}/health" || echo "000")

    if [ "${status_code}" = "200" ]; then
        emit_counter "health_check_success"
    else
        emit_counter "health_check_failure" 1 "code=${status_code}"
        log_warn "Health check returned: ${status_code}"
    fi

    local mem_mb
    mem_mb=$(curl -s "http://${APP_HOST}:${APP_PORT}/metrics/memory" 2>/dev/null \
        | grep "^mem_rss_mb" | awk '{print $2}' || echo "0")
    emit_gauge "memory_rss_mb" "${mem_mb}"

    record_duration "health_check" "${start_ns}"
}

run_background_check() {
    collect_metrics &
    wait
}

while true; do
    run_background_check
    sleep "${INTERVAL}"
done
