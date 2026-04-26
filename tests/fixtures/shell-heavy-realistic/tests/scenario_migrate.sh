#!/usr/bin/env bash
# Scenario: migration dry-run with if-then-return error pattern.

DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-appdb}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"

validate_migration_file() {
    local file="$1"
    if [ ! -f "${file}" ]; then
        echo "[SCENARIO_MIGRATE] File not found: ${file}" >&2
        return 1
    fi
    if [ ! -r "${file}" ]; then
        echo "[SCENARIO_MIGRATE] Not readable: ${file}" >&2
        return 1
    fi
    local size
    size=$(wc -c < "${file}")
    if [ "${size}" -eq 0 ]; then
        echo "[SCENARIO_MIGRATE] Empty migration file: ${file}" >&2
        return 1
    fi
}

dry_run_migration() {
    local file="$1"
    validate_migration_file "${file}" || return 1
    echo "[DRY-RUN] Would apply: $(basename "${file}")"
    grep -c "^[^-]" "${file}" && echo "statements: ok"
}

if [ ! -d "${MIGRATIONS_DIR}" ]; then
    echo "[SCENARIO_MIGRATE] Migrations dir not found: ${MIGRATIONS_DIR}" >&2
    exit 1
fi

found=0
for f in "${MIGRATIONS_DIR}"/*.sql; do
    [ -f "${f}" ] || continue
    dry_run_migration "${f}" || { echo "[SCENARIO_MIGRATE] Invalid: ${f}"; exit 1; }
    found=$(( found + 1 ))
done

echo "[SCENARIO_MIGRATE] Dry-run complete: ${found} migrations validated"
