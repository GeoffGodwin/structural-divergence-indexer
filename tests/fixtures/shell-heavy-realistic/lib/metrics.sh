#!/usr/bin/env bash
# Metrics emission utilities.

source logging.sh

METRICS_ENDPOINT="${METRICS_ENDPOINT:-http://localhost:9091/metrics}"
METRICS_PREFIX="${METRICS_PREFIX:-app}"

emit_counter() {
    local name="$1"
    local value="${2:-1}"
    local labels="${3:-}"
    local full_name="${METRICS_PREFIX}_${name}"
    printf '# TYPE %s counter\n%s{%s} %s\n' \
        "${full_name}" "${full_name}" "${labels}" "${value}" \
        | curl -s -X POST --data-binary @- "${METRICS_ENDPOINT}" >/dev/null
}

emit_gauge() {
    local name="$1"
    local value="$2"
    local labels="${3:-}"
    local full_name="${METRICS_PREFIX}_${name}"
    printf '# TYPE %s gauge\n%s{%s} %s\n' \
        "${full_name}" "${full_name}" "${labels}" "${value}" \
        | curl -s -X POST --data-binary @- "${METRICS_ENDPOINT}" >/dev/null
}

emit_histogram() {
    local name="$1"
    local value="$2"
    local bucket="${3:-0.5}"
    local full_name="${METRICS_PREFIX}_${name}"
    log_debug "Emitting histogram ${full_name}=${value} bucket=${bucket}"
    printf '%s_bucket{le="%s"} 1\n%s_sum %s\n%s_count 1\n' \
        "${full_name}" "${bucket}" "${full_name}" "${value}" "${full_name}" \
        | curl -s -X POST --data-binary @- "${METRICS_ENDPOINT}" >/dev/null
}

record_duration() {
    local name="$1"
    local start_ns="$2"
    local end_ns
    end_ns=$(date +%s%N)
    local duration_ms=$(( (end_ns - start_ns) / 1000000 ))
    emit_histogram "${name}_duration_ms" "${duration_ms}"
}
