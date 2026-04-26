#!/usr/bin/env bash
# Build the application container image.

set -euo pipefail

source ../lib/common.sh
source ../lib/logging.sh
source ../lib/errors.sh

BUILD_TAG="${1:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
REGISTRY="${REGISTRY:-registry.example.com}"
IMAGE_NAME="${IMAGE_NAME:-app}"
FULL_TAG="${REGISTRY}/${IMAGE_NAME}:${BUILD_TAG}"

log_info "Building image: ${FULL_TAG}"

check_cmd docker

setup_error_trap

clean_build_artifacts() {
    log_info "Cleaning previous artifacts"
    rm -rf dist/ build/ *.egg-info/ 2>/dev/null || true
}

run_tests() {
    log_info "Running unit tests before build"
    if ! python -m pytest tests/unit/ -q 2>&1; then
        log_error "Tests failed; aborting build"
        exit 1
    fi
}

build_image() {
    local tag="$1"
    log_info "Building Docker image"
    docker build \
        --tag "${tag}" \
        --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --build-arg VCS_REF="${BUILD_TAG}" \
        .
}

push_image() {
    local tag="$1"
    log_info "Pushing image: ${tag}"
    docker push "${tag}" || { log_error "Push failed"; exit 1; }
}

clean_build_artifacts
run_tests
build_image "${FULL_TAG}"
push_image "${FULL_TAG}"
log_info "Build complete: ${FULL_TAG}"
