#!/usr/bin/env bash
set -euo pipefail

restore() {
    local db="$1"
    local file="$2"
    if [ ! -f "${file}" ]; then
        echo "Backup file not found: ${file}" >&2
        exit 1
    fi
    echo "Restoring ${db} from ${file}"
    psql -U admin -d "${db}" < "${file}"
    echo "Restore complete"
}

restore "${1:-production}" "${2:-backup.sql}"
