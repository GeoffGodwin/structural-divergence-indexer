#!/usr/bin/env bash
# Status command — sources lib/common.sh only (1 edge)
set -euo pipefail

source ../lib/common.sh

show_status() {
    log_info "Service status: OK"
    say "All systems nominal"
}
