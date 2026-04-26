#!/usr/bin/env bash
# Initial environment setup: dependencies, database, schema.

set -euo pipefail

source ../lib/common.sh
source ../lib/logging.sh
source ../lib/db.sh
source ../lib/config.sh

log_info "Starting environment setup"

check_cmd psql
check_cmd docker
check_cmd kubectl

load_config || log_warn "No config file found; using environment variables"

validate_config DB_HOST DB_NAME DB_USER || die "Missing database configuration"

ensure_schema() {
    log_info "Ensuring database schema exists"
    db_query "CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL,
        applied_at TIMESTAMP DEFAULT NOW()
    )" || { log_error "Schema creation failed"; exit 1; }
}

seed_config_table() {
    log_info "Seeding configuration table"
    db_query "INSERT INTO app_config(key, value) VALUES
        ('version', '1.0.0'),
        ('maintenance', 'false')
        ON CONFLICT (key) DO NOTHING"
}

install_dependencies() {
    log_info "Installing application dependencies"
    if command -v pip >/dev/null 2>&1; then
        pip install -q -r requirements.txt || die "pip install failed"
    fi
}

wait_for_db 30 || die "Database not available"
ensure_schema
seed_config_table
install_dependencies
log_info "Setup complete"
