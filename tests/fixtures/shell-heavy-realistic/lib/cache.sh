#!/usr/bin/env bash
# Cache utilities using redis-cli.

source config.sh

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
CACHE_TTL="${CACHE_TTL:-300}"

cache_set() {
    local key="$1"
    local value="$2"
    local ttl="${3:-${CACHE_TTL}}"
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" \
        SET "${key}" "${value}" EX "${ttl}" >/dev/null
}

cache_get() {
    local key="$1"
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" GET "${key}"
}

cache_del() {
    local key="$1"
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DEL "${key}" >/dev/null
}

cache_exists() {
    local key="$1"
    local result
    result=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" EXISTS "${key}")
    [ "${result}" = "1" ]
}

cache_flush() {
    local pattern="${1:-*}"
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" \
        KEYS "${pattern}" | xargs redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" DEL
}

cache_ping() {
    redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" PING >/dev/null 2>&1
}
