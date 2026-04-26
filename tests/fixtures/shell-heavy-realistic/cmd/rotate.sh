#!/usr/bin/env bash
# Rotate authentication secrets and invalidate existing tokens.

set -euo pipefail

source ../lib/common.sh
source ../lib/auth.sh

SECRET_TYPE="${1:-api-key}"

log_info "Rotating ${SECRET_TYPE}"

check_cmd jq

require_var CLIENT_ID "${CLIENT_ID:-}"
require_var CLIENT_SECRET "${CLIENT_SECRET:-}"

case "${SECRET_TYPE}" in
    api-key)
        log_info "Generating new API key"
        new_key=$(curl -fsSL -X POST \
            -H "Authorization: Bearer $(ensure_token "${CLIENT_ID}" "${CLIENT_SECRET}")" \
            "${API_URL:-http://localhost:8080}/admin/rotate-key" \
            | jq -r '.new_key') || die "Key rotation failed"
        log_info "New API key generated (length=${#new_key})"
        ;;
    session)
        log_info "Invalidating all sessions"
        curl -fsSL -X POST \
            -H "Authorization: Bearer $(load_token)" \
            "${API_URL:-http://localhost:8080}/admin/invalidate-sessions" \
            >/dev/null || die "Session invalidation failed"
        ;;
    token)
        log_info "Forcing token refresh"
        rm -f "${TOKEN_FILE:-/tmp/.app_token}"
        ensure_token "${CLIENT_ID}" "${CLIENT_SECRET}" >/dev/null \
            || die "Token refresh failed"
        ;;
    *)
        echo "Usage: $0 {api-key|session|token}" >&2
        exit 2
        ;;
esac

log_info "Rotation complete: ${SECRET_TYPE}"
