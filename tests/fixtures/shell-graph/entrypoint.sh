#!/usr/bin/env bash
# Main entrypoint — dispatches to cmd/* scripts.
# Sources: lib/common.sh, cmd/deploy.sh, cmd/rollback.sh, cmd/status.sh (4 edges)
set -euo pipefail

source lib/common.sh
source cmd/deploy.sh
source cmd/rollback.sh
source cmd/status.sh

main() {
    local cmd="${1:-deploy}"
    case "${cmd}" in
        deploy)   deploy_env "${2:-staging}" ;;
        rollback) rollback_to "${2:-0}" ;;
        status)   show_status ;;
        *) log_error "Unknown command: ${cmd}"; exit 1 ;;
    esac
}

main "$@"
