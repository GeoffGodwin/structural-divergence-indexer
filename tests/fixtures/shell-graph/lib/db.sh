#!/usr/bin/env bash
# Database connection and migration helpers.

db_connect() {
    local host="${DB_HOST:-localhost}"
    local port="${DB_PORT:-5432}"
    printf 'Connecting to %s:%s\n' "${host}" "${port}"
}

db_migrate() {
    local direction="${1:-up}"
    printf 'Running migration: %s\n' "${direction}"
}

db_health() {
    db_connect && printf 'DB healthy\n'
}
