#!/usr/bin/env bash
# Deploy the application to the target environment.

set -euo pipefail

source ../lib/common.sh
source ../lib/logging.sh
source ../lib/network.sh

DEPLOY_ENV="${1:-staging}"
IMAGE_TAG="${2:-latest}"
NAMESPACE="${DEPLOY_ENV}"

log_info "Starting deployment: env=${DEPLOY_ENV} tag=${IMAGE_TAG}"

check_cmd kubectl
require_var KUBECONFIG "${KUBECONFIG:-}"

trap 'log_error "Deployment failed at line $LINENO"; exit 1' ERR

pre_deploy_checks() {
    log_info "Running pre-deploy checks"
    check_connectivity || die "No network connectivity"
    kubectl cluster-info >/dev/null 2>&1 || die "Cluster not reachable"
}

deploy_image() {
    local tag="$1"
    log_info "Deploying image tag=${tag}"
    kubectl -n "${NAMESPACE}" set image deployment/app "app=${REGISTRY:-registry.example.com}/app:${tag}"
    kubectl -n "${NAMESPACE}" rollout status deployment/app --timeout=120s
}

post_deploy_verify() {
    log_info "Verifying deployment"
    wait_for_port "${APP_HOST:-app.${NAMESPACE}.svc}" 8080 60
    local health
    health=$(http_get "/health")
    echo "${health}" | grep -q '"status":"ok"' || die "Health check failed after deploy"
}

pre_deploy_checks
deploy_image "${IMAGE_TAG}"
post_deploy_verify
log_info "Deployment complete: env=${DEPLOY_ENV} tag=${IMAGE_TAG}"
