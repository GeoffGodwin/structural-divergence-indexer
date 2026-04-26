#!/usr/bin/env bash
# Stop the application service gracefully.

set -e

source ../lib/common.sh
source ../lib/logging.sh

PID_FILE="${PID_FILE:-/var/run/app.pid}"
GRACE_PERIOD="${GRACE_PERIOD:-15}"

log_info "Stopping application (grace=${GRACE_PERIOD}s)"

if [ ! -f "${PID_FILE}" ]; then
    log_warn "PID file not found: ${PID_FILE}; nothing to stop"
    exit 0
fi

pid=$(cat "${PID_FILE}")

if ! kill -0 "${pid}" 2>/dev/null; then
    log_warn "Process ${pid} not running; cleaning up PID file"
    rm -f "${PID_FILE}"
    exit 0
fi

log_info "Sending SIGTERM to pid=${pid}"
kill -TERM "${pid}"

elapsed=0
while kill -0 "${pid}" 2>/dev/null; do
    sleep 1
    elapsed=$(( elapsed + 1 ))
    if [ "${elapsed}" -ge "${GRACE_PERIOD}" ]; then
        log_warn "Grace period elapsed; sending SIGKILL to pid=${pid}"
        kill -KILL "${pid}" 2>/dev/null || true
        break
    fi
done

rm -f "${PID_FILE}"
log_info "Application stopped"
