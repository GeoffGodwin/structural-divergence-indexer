#!/usr/bin/env bash
# Scenario: build verification with test-command-substitution error pattern.

BUILD_DIR="${1:-.}"
STATUS_FILE="${BUILD_DIR}/.build_status"

check_artifacts() {
    local dir="$1"
    if [ ! "$(ls -A "${dir}/dist/" 2>/dev/null)" ]; then
        echo "[SCENARIO_BUILD] No artifacts in ${dir}/dist" >&2
        return 1
    fi
}

verify_checksum() {
    local file="$1"
    local expected_sum="$2"
    local actual_sum
    actual_sum=$(sha256sum "${file}" | awk '{print $1}')
    if [ "${actual_sum}" != "${expected_sum}" ]; then
        echo "[SCENARIO_BUILD] Checksum mismatch: ${file}" >&2
        return 1
    fi
}

run_linter() {
    local dir="$1"
    if ! output=$(python -m ruff check "${dir}" 2>&1); then
        echo "[SCENARIO_BUILD] Lint failures:" >&2
        echo "${output}" >&2
        return 1
    fi
}

check_artifacts "${BUILD_DIR}" || exit 1
run_linter "${BUILD_DIR}" || exit 1
echo "build: ok" > "${STATUS_FILE}"
echo "[SCENARIO_BUILD] Build verification passed"
