#!/usr/bin/env bash
# General-purpose string utilities (no external dependencies).

trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "${s}"
}

to_upper() { printf '%s' "${1}" | tr '[:lower:]' '[:upper:]'; }
to_lower() { printf '%s' "${1}" | tr '[:upper:]' '[:lower:]'; }
