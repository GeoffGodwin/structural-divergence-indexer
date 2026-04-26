#!/usr/bin/env bash
# Clean up stale resources: cache, temp files, old artifacts.

set -e

source ../lib/common.sh
source ../lib/config.sh
source ../lib/cache.sh

TEMP_DIR="${TEMP_DIR:-/tmp/app}"
ARTIFACT_DIR="${ARTIFACT_DIR:-./dist}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:-7}"

log_info "Starting cleanup: temp=${TEMP_DIR} artifacts=${ARTIFACT_DIR}"

load_config || true

cleanup_temp_files() {
    if [ ! -d "${TEMP_DIR}" ]; then
        log_info "Temp dir not found: ${TEMP_DIR}; skipping"
        return 0
    fi
    local count
    count=$(find "${TEMP_DIR}" -type f -mtime "+${MAX_AGE_DAYS}" | wc -l)
    log_info "Removing ${count} temp files older than ${MAX_AGE_DAYS} days"
    find "${TEMP_DIR}" -type f -mtime "+${MAX_AGE_DAYS}" -delete
}

cleanup_artifacts() {
    if [ ! -d "${ARTIFACT_DIR}" ]; then
        log_info "Artifact dir not found: ${ARTIFACT_DIR}; skipping"
        return 0
    fi
    local count
    count=$(find "${ARTIFACT_DIR}" -name "*.tar.gz" -mtime "+${MAX_AGE_DAYS}" | wc -l)
    log_info "Removing ${count} artifact archives"
    find "${ARTIFACT_DIR}" -name "*.tar.gz" -mtime "+${MAX_AGE_DAYS}" -delete
}

cleanup_cache() {
    log_info "Flushing expired cache entries"
    cache_ping || { log_warn "Cache not available; skipping cache cleanup"; return 0; }
    cache_flush "expired:*"
    cache_flush "tmp:*"
}

cleanup_temp_files
cleanup_artifacts
cleanup_cache
log_info "Cleanup complete"
