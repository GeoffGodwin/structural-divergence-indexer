#!/usr/bin/env bash
# Scenario: basic run with nonzero-exit error pattern (unique shape: set -E + trap combo).

set -E
set -o nounset

ERR_COUNT=0

on_error() {
    ERR_COUNT=$(( ERR_COUNT + 1 ))
    echo "[SCENARIO_RUN] Error ${ERR_COUNT} at line $LINENO" >&2
}
trap on_error ERR

run_step() {
    local step="$1"
    echo "Running step: ${step}"
    curl -fsSL "http://localhost:8080/steps/${step}" >/dev/null 2>&1
}

run_step "init"
run_step "process"
run_step "finalize"

if [ "${ERR_COUNT}" -gt 0 ]; then
    echo "[SCENARIO_RUN] Completed with ${ERR_COUNT} non-fatal errors" >&2
    exit 1
fi
echo "[SCENARIO_RUN] All steps complete"
