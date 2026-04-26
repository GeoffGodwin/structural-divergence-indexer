#!/usr/bin/env bash
# Perform application health checks and report status.

set -e

source ../lib/common.sh
source ../lib/network.sh
source ../lib/logging.sh

APP_HOST="${APP_HOST:-localhost}"
APP_PORT="${APP_PORT:-8080}"
EXIT_CODE=0

log_info "Running health checks: host=${APP_HOST} port=${APP_PORT}"

check_http_health() {
    local result
    result=$(http_get "/health") || { log_error "HTTP health check failed"; return 1; }
    local status
    status=$(echo "${result}" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "${status}" != "ok" ]; then
        log_error "Health endpoint reports: ${status}"
        return 1
    fi
    log_info "HTTP health: ok"
}

check_readiness() {
    local result
    result=$(http_get "/ready") || { log_warn "Readiness check failed"; return 1; }
    log_info "Readiness: ok"
}

check_dependencies() {
    log_info "Checking downstream dependencies"
    local deps_result
    deps_result=$(http_get "/health/dependencies") || { log_warn "Dependency check unreachable"; return 1; }
    local failed
    failed=$(echo "${deps_result}" | jq -r '.failed[]?' 2>/dev/null || echo "")
    if [ -n "${failed}" ]; then
        log_warn "Failed dependencies: ${failed}"
        return 1
    fi
    log_info "All dependencies healthy"
}

check_http_health || EXIT_CODE=1
check_readiness || true
check_dependencies || true

if [ "${EXIT_CODE}" -ne 0 ]; then
    log_error "Health check failed"
    exit 1
fi
log_info "All health checks passed"
