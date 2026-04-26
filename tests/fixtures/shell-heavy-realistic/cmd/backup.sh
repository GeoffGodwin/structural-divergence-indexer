#!/usr/bin/env bash
# Trigger an on-demand backup of the database.

set -e

source ../lib/common.sh
source ../lib/db.sh
source ../lib/logging.sh

DEST="${1:-}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
DEST="${DEST:-./backup_${TIMESTAMP}.dump}"

log_info "On-demand backup: dest=${DEST}"

require_var DB_HOST "${DB_HOST:-}"

wait_for_db 10 || die "Database not reachable"

log_info "Starting database dump"
db_dump "${DEST}" || { log_error "Backup failed"; exit 1; }

size=$(du -sh "${DEST}" | cut -f1)
log_info "Backup complete: ${DEST} (${size})"
audit_log "backup" "${DEST}"
