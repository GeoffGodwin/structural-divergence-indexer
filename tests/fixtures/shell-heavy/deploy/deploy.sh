#!/usr/bin/env bash
set -euo pipefail

source ../lib/common.sh

cleanup() {
    log_info "Cleanup triggered"
    log_error "Deploy failed — rolling back"
}
trap cleanup ERR

run_healthcheck() {
    local url="$1"
    curl -sf "${url}" || exit 1
    log_info "Health check passed: ${url}"
}

deploy_manifests() {
    local env="$1"
    kubectl apply -f "manifests/${env}.yaml" &
    wait
    log_info "Manifests applied for ${env}"
}

main() {
    local env="${1:-staging}"
    require_var "env" "${env}"
    run_healthcheck "http://health.example.com/ready"
    deploy_manifests "${env}"
}

main "$@"
