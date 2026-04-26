#!/usr/bin/env bash
# Manage authentication tokens and credentials.

set -euo pipefail

source ../lib/common.sh
source ../lib/auth.sh
source ../lib/logging.sh

COMMAND="${1:-status}"

check_cmd curl
check_cmd jq

require_var AUTH_URL "${AUTH_URL:-}"
require_var CLIENT_ID "${CLIENT_ID:-}"
require_var CLIENT_SECRET "${CLIENT_SECRET:-}"

case "${COMMAND}" in
    login)
        log_info "Fetching authentication token"
        token=$(fetch_token "${CLIENT_ID}" "${CLIENT_SECRET}") \
            || die "Token fetch failed"
        save_token "${token}"
        log_info "Token saved"
        ;;
    verify)
        log_info "Verifying current token"
        token=$(load_token) || die "No token found; run login first"
        valid=$(verify_token "${token}")
        if [ "${valid}" = "true" ]; then
            log_info "Token is valid"
        else
            log_error "Token is invalid or expired"
            exit 1
        fi
        ;;
    refresh)
        log_info "Refreshing token if expired"
        token=$(ensure_token "${CLIENT_ID}" "${CLIENT_SECRET}") \
            || die "Token refresh failed"
        log_info "Token ready"
        ;;
    status)
        if token_expired; then
            echo "Token: expired or not present"
        else
            echo "Token: valid"
        fi
        ;;
    *)
        echo "Usage: $0 {login|verify|refresh|status}" >&2
        exit 2
        ;;
esac
