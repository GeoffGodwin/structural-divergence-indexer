#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    echo "Backup cleanup" >&2
}
trap cleanup ERR EXIT

backup_db() {
    local db="$1"
    local out="backup_${db}.sql"
    echo "Backing up ${db}"
    pg_dump -U admin -d "${db}" > "${out}"
    echo "Backup written to ${out}"
}

backup_db "${1:-production}"
