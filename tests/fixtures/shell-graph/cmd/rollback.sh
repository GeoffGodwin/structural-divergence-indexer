#!/usr/bin/env bash
# Rollback command — sources lib/common.sh, lib/log.sh, lib/db.sh (3 edges)
set -euo pipefail

source ../lib/common.sh
source ../lib/log.sh
source ../lib/db.sh

rollback_to() {
    local version="${1:-0}"
    log_info "Rolling back to version ${version}"
    db_migrate down
    log_info "Rollback complete"
}
