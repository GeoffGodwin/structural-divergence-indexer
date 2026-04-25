#!/usr/bin/env bash
set -euo pipefail

check_url() {
    local url="$1"
    curl -sf "${url}" || return 1
    echo "OK: ${url}"
}

check_all() {
    local base_url="$1"
    check_url "${base_url}/health" &
    check_url "${base_url}/ready" &
    wait
}

check_all "${1:-http://localhost:8080}"
