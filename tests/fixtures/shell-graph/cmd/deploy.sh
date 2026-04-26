#!/usr/bin/env bash
# Deploy command — sources lib/common.sh, lib/log.sh, lib/db.sh (3 edges)
set -euo pipefail

source ../lib/common.sh
source ../lib/log.sh
source ../lib/db.sh

deploy_env() {
    local env="${1:-staging}"
    log_info "Deploying to ${env}"
    require_env "DEPLOY_TOKEN"
    db_migrate up
    log_info "Deploy complete for ${env}"
}
