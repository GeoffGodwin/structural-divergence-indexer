#!/usr/bin/env bash
# Reset application state: flush cache and truncate ephemeral tables.

set -euo pipefail

source ../lib/common.sh
source ../lib/db.sh
source ../lib/cache.sh

CONFIRM="${CONFIRM:-}"

if [ -z "${CONFIRM}" ]; then
    echo "WARNING: This will reset all ephemeral application state."
    echo "Set CONFIRM=yes to proceed."
    exit 2
fi

[ "${CONFIRM}" = "yes" ] || { echo "CONFIRM must be 'yes'"; exit 2; }

log_info "Resetting application state"

require_var DB_HOST "${DB_HOST:-}"

flush_cache() {
    log_info "Flushing all cache entries"
    cache_ping || { log_warn "Cache not reachable; skipping flush"; return 0; }
    cache_flush "*"
}

reset_db_state() {
    log_info "Truncating ephemeral tables"
    db_query "TRUNCATE TABLE sessions, rate_limits, temp_tokens CASCADE" \
        || { log_error "Table truncation failed"; exit 1; }
    db_query "DELETE FROM job_queue WHERE status IN ('pending', 'failed')"
}

wait_for_db 10 || die "Database not available"
flush_cache
reset_db_state
log_info "Reset complete"
