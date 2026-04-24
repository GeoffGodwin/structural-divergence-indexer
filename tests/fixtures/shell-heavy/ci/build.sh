#!/usr/bin/env bash
set -euo pipefail

source ../lib/common.sh

log_info "Starting build"

VERSION=$(jq -r '.version' package.json)
log_info "Building version: ${VERSION}"

if [ -z "$(which docker)" ]; then
    log_error "docker not found in PATH"
    exit 1
fi

find . -name "*.sh" | xargs -P 4 shellcheck
echo "Lint complete"
