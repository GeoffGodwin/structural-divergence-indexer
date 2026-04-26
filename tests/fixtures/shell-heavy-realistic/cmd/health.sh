#!/usr/bin/env bash
# Quick health check: HTTP endpoint + database reachability.

set -e

source ../lib/common.sh
source ../lib/network.sh
source ../lib/db.sh

APP_HOST="${APP_HOST:-localhost}"
APP_PORT="${APP_PORT:-8080}"
OVERALL_STATUS=0

check_app_http() {
    if http_get "/health" >/dev/null 2>&1; then
        echo "app_http: ok"
    else
        echo "app_http: FAIL"
        OVERALL_STATUS=1
    fi
}

check_database() {
    if db_connect_check 2>/dev/null; then
        echo "database: ok"
    else
        echo "database: FAIL"
        OVERALL_STATUS=1
    fi
}

check_app_http
check_database

if [ "${OVERALL_STATUS}" -ne 0 ]; then
    echo "health: DEGRADED"
    exit 1
fi
echo "health: ok"
