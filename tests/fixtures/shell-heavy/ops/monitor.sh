#!/usr/bin/env bash
set -euo pipefail

check_endpoints() {
    local base="$1"
    curl -sf "${base}/metrics" | jq '.status' || return 1
    echo "Metrics collected"
}

check_redis() {
    local host="${1:-localhost}"
    redis-cli -h "${host}" ping || exit 1
    echo "Redis OK"
}

# Parallelise endpoint checks across environment list
printf '%s\n' staging production | xargs -P 2 -I{} bash -c 'curl -sf "http://{}.example.com/health"'

check_endpoints "http://localhost:9090"
check_redis
