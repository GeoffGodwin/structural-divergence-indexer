#!/usr/bin/env bash
# Configuration loading and validation.

CONFIG_FILE="${CONFIG_FILE:-./config.env}"
CONFIG_LOADED=0

load_config() {
    local cfg_file="${1:-${CONFIG_FILE}}"
    if [ ! -f "${cfg_file}" ]; then
        echo "[CONFIG] Config file not found: ${cfg_file}" >&2
        return 1
    fi
    # shellcheck disable=SC1090
    source "${cfg_file}"
    CONFIG_LOADED=1
}

require_config() {
    if [ "${CONFIG_LOADED}" -ne 1 ]; then
        echo "[CONFIG] Config not loaded; call load_config first" >&2
        exit 2
    fi
}

get_config() {
    local key="$1"
    local default="${2:-}"
    local val
    val=$(printenv "${key}" 2>/dev/null || echo "${default}")
    echo "${val}"
}

validate_config() {
    local required_keys="$@"
    for key in ${required_keys}; do
        val=$(get_config "${key}")
        if [ -z "${val}" ]; then
            echo "[CONFIG] Missing required config key: ${key}" >&2
            return 1
        fi
    done
}

dump_config() {
    env | grep -E "^(APP_|DB_|API_)" | sort
}
