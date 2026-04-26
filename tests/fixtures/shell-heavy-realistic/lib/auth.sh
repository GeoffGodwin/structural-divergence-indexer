#!/usr/bin/env bash
# Auth and credential utilities.

source common.sh
source db.sh

TOKEN_FILE="${TOKEN_FILE:-/tmp/.app_token}"
TOKEN_TTL="${TOKEN_TTL:-3600}"

fetch_token() {
    local client_id="$1"
    local client_secret="$2"
    curl -fsSL -X POST \
        -d "client_id=${client_id}&client_secret=${client_secret}&grant_type=client_credentials" \
        "${AUTH_URL:-http://localhost:9000}/token" \
        | jq -r '.access_token'
}

save_token() {
    local token="$1"
    echo "${token}" > "${TOKEN_FILE}"
    chmod 600 "${TOKEN_FILE}"
}

load_token() {
    if [ ! -f "${TOKEN_FILE}" ]; then
        echo "[AUTH] Token file not found" >&2
        return 1
    fi
    cat "${TOKEN_FILE}"
}

token_expired() {
    if [ ! -f "${TOKEN_FILE}" ]; then
        return 0
    fi
    local mtime now age
    mtime=$(stat -c %Y "${TOKEN_FILE}" 2>/dev/null || stat -f %m "${TOKEN_FILE}")
    now=$(date +%s)
    age=$(( now - mtime ))
    [ "${age}" -gt "${TOKEN_TTL}" ]
}

ensure_token() {
    local client_id="$1"
    local client_secret="$2"
    if token_expired; then
        local token
        token=$(fetch_token "${client_id}" "${client_secret}") || return 1
        save_token "${token}"
    fi
    load_token
}

verify_token() {
    local token="$1"
    local result
    result=$(curl -fsSL -H "Authorization: Bearer ${token}" \
        "${AUTH_URL:-http://localhost:9000}/verify")
    echo "${result}" | jq -r '.valid'
}
