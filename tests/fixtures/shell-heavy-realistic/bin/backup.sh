#!/usr/bin/env bash
# Backup database and application state.

set -euo pipefail

source ../lib/common.sh
source ../lib/db.sh
source ../lib/logging.sh
source ../lib/cache.sh

BACKUP_DIR="${BACKUP_DIR:-/var/backups/app}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.dump"

log_info "Starting backup: dir=${BACKUP_DIR}"

require_var DB_HOST "${DB_HOST:-}"

check_cmd pg_dump

mkdir -p "${BACKUP_DIR}" || die "Cannot create backup dir: ${BACKUP_DIR}"

pre_backup_cache_flush() {
    log_info "Flushing cache before backup"
    cache_ping && cache_flush "stale:*" || log_warn "Cache flush skipped (not available)"
}

run_db_backup() {
    log_info "Dumping database to ${BACKUP_FILE}"
    db_dump "${BACKUP_FILE}" || { log_error "Database dump failed"; exit 1; }
    log_info "Backup written: $(du -sh "${BACKUP_FILE}" | cut -f1)"
}

prune_old_backups() {
    log_info "Pruning backups older than ${RETENTION_DAYS} days"
    find "${BACKUP_DIR}" -name "db_*.dump" -mtime "+${RETENTION_DAYS}" -delete
    local remaining
    remaining=$(find "${BACKUP_DIR}" -name "db_*.dump" | wc -l)
    log_info "Retained ${remaining} backup files"
}

upload_to_s3() {
    local file="$1"
    local bucket="${S3_BUCKET:-}"
    if [ -z "${bucket}" ]; then
        log_info "S3_BUCKET not set; skipping upload"
        return 0
    fi
    aws s3 cp "${file}" "s3://${bucket}/backups/$(basename "${file}")" || \
        log_warn "S3 upload failed; local backup retained"
}

pre_backup_cache_flush
run_db_backup
upload_to_s3 "${BACKUP_FILE}"
prune_old_backups
log_info "Backup complete: ${BACKUP_FILE}"
