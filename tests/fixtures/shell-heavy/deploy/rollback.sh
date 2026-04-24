#!/usr/bin/env bash
set -euo pipefail

source ../lib/common.sh

rollback() {
    local app="$1"
    log_info "Rolling back ${app}"
    if ! kubectl rollout status "deployment/${app}"; then
        log_error "Rollout status check failed"
        exit 1
    fi
    kubectl rollout undo "deployment/${app}"
    log_info "Rollback complete for ${app}"
}

rollback "${1:-myapp}"
