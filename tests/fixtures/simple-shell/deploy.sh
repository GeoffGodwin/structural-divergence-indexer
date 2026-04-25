#!/usr/bin/env bash
set -euo pipefail

source ./lib/util.sh

cleanup() {
    echo "Cleaning up deployment artifacts"
    logger "deploy: cleanup triggered"
}

trap cleanup ERR

deploy() {
    local env="$1"
    echo "Starting deployment to ${env}"
    do_deploy "${env}" || exit 1
}

deploy "${1:-staging}"
