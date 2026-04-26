#!/usr/bin/env bash
# Scenario: rollback procedure with trap-EXIT error pattern (unique to scenario files).

ROLLBACK_TARGET="${1:-}"
ROLLBACK_LOG="/tmp/rollback_$(date +%s).log"

cleanup_on_exit() {
    local exit_code=$?
    if [ "${exit_code}" -ne 0 ]; then
        echo "[SCENARIO_ROLLBACK] Rollback failed (code=${exit_code})" | tee -a "${ROLLBACK_LOG}" >&2
    fi
    rm -f "/tmp/.rollback_lock"
}
trap cleanup_on_exit EXIT

if [ -z "${ROLLBACK_TARGET}" ]; then
    echo "[SCENARIO_ROLLBACK] Usage: $0 <target-version>" >&2
    exit 2
fi

acquire_lock() {
    if ! mkdir "/tmp/.rollback_lock" 2>/dev/null; then
        echo "[SCENARIO_ROLLBACK] Another rollback in progress" >&2
        exit 1
    fi
}

validate_target() {
    local target="$1"
    if ! echo "${target}" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
        echo "[SCENARIO_ROLLBACK] Invalid version format: ${target}" >&2
        exit 2
    fi
}

acquire_lock
validate_target "${ROLLBACK_TARGET}"
echo "[SCENARIO_ROLLBACK] Rolling back to ${ROLLBACK_TARGET}" | tee -a "${ROLLBACK_LOG}"
kubectl rollout undo deployment/app --to-revision="${ROLLBACK_TARGET}" \
    || { echo "[SCENARIO_ROLLBACK] kubectl rollout undo failed" >&2; exit 1; }
echo "[SCENARIO_ROLLBACK] Complete"
