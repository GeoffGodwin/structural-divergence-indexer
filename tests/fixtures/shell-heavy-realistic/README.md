# shell-heavy-realistic fixture

Synthetic shell fixture simulating a production DevOps toolchain. Used by
`tests/integration/test_validation_shell_realistic.py` to assert that the
M15 source-resolution, M16 per-language entropy, and M17 scope_exclude
pipeline stages all produce correct signal on a realistic shell codebase.

## Structure

| Directory | Files | Role |
|---|---|---|
| `lib/` | 9 scripts | Shared utilities (leaf nodes and a small cross-lib DAG) |
| `bin/` | 9 scripts | Top-level operational commands (each sources 2–4 lib files) |
| `cmd/` | 9 scripts | Service management commands (each sources 2–3 lib files) |
| `tests/` | 5 scripts | Scenario scripts with deliberately distinct error_handling shapes |

**Total shell files: 32** (within the 30–40 range asserted by the test).

## Source Edge Count (manually counted)

### lib/ cross-edges (6 total)
| Importer | Sources |
|---|---|
| lib/db.sh | lib/config.sh, lib/logging.sh |
| lib/auth.sh | lib/common.sh, lib/db.sh |
| lib/cache.sh | lib/config.sh |
| lib/metrics.sh | lib/logging.sh |

### bin/ edges (29 total)
| Script | Sources |
|---|---|
| bin/deploy.sh | lib/common.sh, lib/logging.sh, lib/network.sh (3) |
| bin/build.sh | lib/common.sh, lib/logging.sh, lib/errors.sh (3) |
| bin/migrate.sh | lib/common.sh, lib/db.sh, lib/config.sh (3) |
| bin/backup.sh | lib/common.sh, lib/db.sh, lib/logging.sh, lib/cache.sh (4) |
| bin/monitor.sh | lib/common.sh, lib/logging.sh, lib/metrics.sh (3) |
| bin/auth.sh | lib/common.sh, lib/auth.sh, lib/logging.sh (3) |
| bin/cleanup.sh | lib/common.sh, lib/config.sh, lib/cache.sh (3) |
| bin/setup.sh | lib/common.sh, lib/logging.sh, lib/db.sh, lib/config.sh (4) |
| bin/healthcheck.sh | lib/common.sh, lib/network.sh, lib/logging.sh (3) |

### cmd/ edges (22 total)
| Script | Sources |
|---|---|
| cmd/start.sh | lib/common.sh, lib/config.sh (2) |
| cmd/stop.sh | lib/common.sh, lib/logging.sh (2) |
| cmd/status.sh | lib/common.sh, lib/metrics.sh (2) |
| cmd/health.sh | lib/common.sh, lib/network.sh, lib/db.sh (3) |
| cmd/reload.sh | lib/common.sh, lib/config.sh, lib/logging.sh (3) |
| cmd/reset.sh | lib/common.sh, lib/db.sh, lib/cache.sh (3) |
| cmd/scale.sh | lib/common.sh, lib/config.sh (2) |
| cmd/rotate.sh | lib/common.sh, lib/auth.sh (2) |
| cmd/backup.sh | lib/common.sh, lib/db.sh, lib/logging.sh (3) |

**Total source edges: 57** (within the 45–60 range; test asserts `>= 45`).

## Pattern Shape Distribution

The fixture is designed to produce at minimum:

| Category | Distinct shapes | Example constructs |
|---|---|---|
| error_handling | ≥ 6 | `set -e`, `set -euo pipefail`, `trap '...' ERR`, `exit 1`, `cmd \|\| exit 1`, `if ! cmd; then exit 1` |
| data_access | ≥ 3 | `curl`, `psql`, `kubectl`, `redis-cli`, `aws`, `pg_dump` |
| logging | ≥ 4 | `echo "plain"`, `printf "%s" "$arg"`, `logger -t`, `echo "..." >&2` |
| async_patterns | ≥ 2 | `cmd &`, `wait` |

**Sum ≥ 15** — satisfies `pattern_entropy_by_language["shell"] >= 15`.

## tests/ Scenario Files

The five `tests/scenario_*.sh` files each contain distinct error_handling
shapes not present in the lib/bin/cmd files. When `scope_exclude = ["tests/**"]`
is configured, `pattern_entropy_by_language["shell"]` decreases measurably.

The test asserts:
- `pattern_catalog.meta.scope_excluded_file_count == 5` (exactly the 5 scenario files)
- `pattern_entropy_by_language["shell"]` after exclusion < baseline value

## Updating the Fixture

If you add or remove source statements, update the edge count table above
and adjust the test assertion floor in `test_validation_shell_realistic.py`
accordingly. The test uses a floor (`>= 45`) not an exact count so minor
changes do not require immediate test updates.
