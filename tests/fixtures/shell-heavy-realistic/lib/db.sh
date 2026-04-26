#!/usr/bin/env bash
# Database utilities: connection, query, migration helpers.

source config.sh
source logging.sh

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-appdb}"
DB_USER="${DB_USER:-app}"

db_connect_check() {
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "SELECT 1" >/dev/null 2>&1 || return 1
}

db_query() {
    local sql="$1"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "${sql}"
}

db_query_csv() {
    local sql="$1"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        --csv -c "${sql}"
}

db_run_file() {
    local sql_file="$1"
    if [ ! -f "${sql_file}" ]; then
        log_error "SQL file not found: ${sql_file}"
        return 1
    fi
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -f "${sql_file}"
}

db_dump() {
    local dest="$1"
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -Fc -f "${dest}"
}

db_restore() {
    local src="$1"
    pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "${src}"
}

wait_for_db() {
    local attempts="${1:-30}"
    local i=0
    while [ "${i}" -lt "${attempts}" ]; do
        db_connect_check && return 0
        i=$(( i + 1 ))
        sleep 2
    done
    log_error "Database not reachable after ${attempts} attempts"
    return 1
}
