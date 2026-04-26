#!/usr/bin/env bash
# Scenario: deployment smoke test with list-node error pattern (cmd && cmd || bail).

TARGET_ENV="${1:-staging}"
ENDPOINT="http://${TARGET_ENV}.example.com"

smoke_test() {
    local path="$1"
    local expected_code="${2:-200}"
    local actual_code
    actual_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 "${ENDPOINT}${path}" 2>/dev/null) || return 1
    [ "${actual_code}" = "${expected_code}" ]
}

check_deploy_and_report() {
    smoke_test "/health" 200 && echo "health: ok" || { echo "health: FAIL" >&2; return 1; }
    smoke_test "/api/v1/status" 200 && echo "api: ok" || { echo "api: FAIL" >&2; return 1; }
    smoke_test "/metrics" 200 && echo "metrics: ok" || echo "metrics: unavailable"
}

MAX_RETRIES=3
attempt=0
while [ "${attempt}" -lt "${MAX_RETRIES}" ]; do
    check_deploy_and_report && break
    attempt=$(( attempt + 1 ))
    echo "[SCENARIO_DEPLOY] Retry ${attempt}/${MAX_RETRIES}" >&2
    sleep 5
done

[ "${attempt}" -lt "${MAX_RETRIES}" ] || { echo "[SCENARIO_DEPLOY] Smoke tests failed" >&2; exit 1; }
echo "[SCENARIO_DEPLOY] Deploy verified on ${TARGET_ENV}"
