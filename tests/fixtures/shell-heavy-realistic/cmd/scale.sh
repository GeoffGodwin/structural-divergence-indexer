#!/usr/bin/env bash
# Scale application replicas up or down.

set -e

source ../lib/common.sh
source ../lib/config.sh

REPLICAS="${1:-}"
NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT="${DEPLOYMENT:-app}"

if [ -z "${REPLICAS}" ]; then
    echo "Usage: $0 <replica-count>" >&2
    exit 2
fi

if ! echo "${REPLICAS}" | grep -qE '^[0-9]+$'; then
    log_error "Invalid replica count: ${REPLICAS}"
    exit 2
fi

check_cmd kubectl

require_var KUBECONFIG "${KUBECONFIG:-}"
load_config || true

current=$(kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" \
    -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "unknown")

log_info "Scaling ${DEPLOYMENT}: ${current} -> ${REPLICAS} replicas"

kubectl -n "${NAMESPACE}" scale deployment "${DEPLOYMENT}" \
    --replicas="${REPLICAS}" || { log_error "Scale command failed"; exit 1; }

kubectl -n "${NAMESPACE}" rollout status deployment/"${DEPLOYMENT}" \
    --timeout=120s

log_info "Scale complete: ${DEPLOYMENT} now at ${REPLICAS} replicas"
