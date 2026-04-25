#!/usr/bin/env bash
set -euo pipefail

run_suite() {
    local suite="$1"
    echo "Running ${suite} tests"
    ./run-tests.sh "${suite}" &
}

run_suite unit
run_suite integration
wait

echo "All test suites complete"
