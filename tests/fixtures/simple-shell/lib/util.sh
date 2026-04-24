#!/usr/bin/env bash
# Shared utilities for deployment scripts.

do_deploy() {
    local env="$1"
    printf "Deploying to %s\\n" "${env}"
}

wait_for_health() {
    local url="$1"
    printf "Waiting for health at %s\\n" "${url}"
}
