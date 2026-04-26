#!/usr/bin/env bash
# Network utilities: HTTP calls, connectivity checks.

HTTP_TIMEOUT="${HTTP_TIMEOUT:-30}"
BASE_URL="${BASE_URL:-http://localhost:8080}"

http_get() {
    local path="$1"
    local url="${BASE_URL}${path}"
    curl -f -s --max-time "${HTTP_TIMEOUT}" "${url}"
}

http_post() {
    local path="$1"
    local payload="$2"
    local url="${BASE_URL}${path}"
    curl -f -s -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        --max-time "${HTTP_TIMEOUT}" \
        "${url}"
}

wait_for_port() {
    local host="$1"
    local port="$2"
    local timeout="${3:-60}"
    local elapsed=0
    while ! curl -s "http://${host}:${port}/health" >/dev/null 2>&1; do
        sleep 2
        elapsed=$(( elapsed + 2 ))
        if [ "${elapsed}" -ge "${timeout}" ]; then
            echo "[NET] Timed out waiting for ${host}:${port}" >&2
            return 1
        fi
    done
}

check_connectivity() {
    local host="${1:-8.8.8.8}"
    if ! curl -s --max-time 5 "https://${host}" >/dev/null 2>&1; then
        echo "[NET] No connectivity to ${host}" >&2
        return 1
    fi
}

download_file() {
    local url="$1"
    local dest="$2"
    curl -fsSL --max-time 120 -o "${dest}" "${url}" || return 1
}
