#!/usr/bin/env bash
# Run database migrations.

set -e

source ../lib/common.sh
source ../lib/db.sh
source ../lib/config.sh

MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"
DRY_RUN="${DRY_RUN:-0}"

log_info "Starting migration: dir=${MIGRATIONS_DIR} dry_run=${DRY_RUN}"

require_var DB_HOST "${DB_HOST:-}"
require_var DB_NAME "${DB_NAME:-}"

load_config || true

wait_for_db 20 || die "Database not available"

list_applied() {
    db_query "SELECT name FROM schema_migrations ORDER BY applied_at" 2>/dev/null \
        | tail -n +3 | head -n -2 | awk '{print $1}' || echo ""
}

apply_migration() {
    local file="$1"
    local name
    name=$(basename "${file}" .sql)
    if [ "${DRY_RUN}" = "1" ]; then
        log_info "[DRY-RUN] Would apply: ${name}"
        return 0
    fi
    log_info "Applying migration: ${name}"
    db_run_file "${file}" || { log_error "Migration failed: ${name}"; exit 1; }
    db_query "INSERT INTO schema_migrations(name) VALUES ('${name}')"
}

applied=$(list_applied)
for migration_file in "${MIGRATIONS_DIR}"/*.sql; do
    [ -f "${migration_file}" ] || continue
    name=$(basename "${migration_file}" .sql)
    if echo "${applied}" | grep -q "^${name}$"; then
        log_info "Already applied: ${name}"
        continue
    fi
    apply_migration "${migration_file}"
done

log_info "Migration complete"
