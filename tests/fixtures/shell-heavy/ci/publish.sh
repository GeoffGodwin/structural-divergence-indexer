#!/usr/bin/env bash
set -euo pipefail

publish() {
    local version="$1"
    echo "Publishing version ${version}"
    aws s3 cp "dist/${version}.tar.gz" "s3://artifacts/${version}/"
    kubectl create configmap "app-version" --from-literal=version="${version}" \
        --dry-run=client -o yaml | kubectl apply -f -
}

trap 'echo "Publish failed" >&2' ERR

publish "${1:-latest}"
