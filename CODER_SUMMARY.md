# Coder Summary
## Status: COMPLETE

## What Was Implemented

Milestone 1: Project Skeleton, Config System, and Core Data Structures — full greenfield implementation.

- **`pyproject.toml`**: PEP 621 metadata, all dependency declarations, entry point `sdi = "sdi.cli:cli"`, extras (`[dev]`, `[all]`, `[web]`, `[systems]`)
- **`src/sdi/__init__.py`**: Package with `__version__ = "0.1.0"`
- **`src/sdi/config.py`**: Complete five-level precedence config loading (`load_config()`), all config dataclasses (`SDIConfig`, `CoreConfig`, `SnapshotsConfig`, `BoundariesConfig`, `PatternsConfig`, `ThresholdsConfig`, `ThresholdOverride`, `ChangeCouplingConfig`, `OutputConfig`), env var overrides, threshold override validation (exit code 2 when `expires` missing), expired override silent skip, unknown key `DeprecationWarning`, TOML parse error with file path (exit code 2)
- **`src/sdi/cli/__init__.py`**: Root Click group with `--format/--no-color/--quiet/--verbose` global flags, custom `_SDIGroup` exception handler (preserves `SystemExit`, wraps unexpected exceptions as exit code 1), 7 placeholder subcommands that exit 1 with "not yet implemented"
- **`src/sdi/cli/init_cmd.py`**: `sdi init` command — git root detection (exit code 2 if not in git repo), creates `.sdi/config.toml` with commented defaults, creates `.sdi/snapshots/`, adds `.sdi/cache/` to `.gitignore`, `--force` flag for reinit
- **`src/sdi/snapshot/__init__.py`**: Public API exports
- **`src/sdi/snapshot/model.py`**: `FeatureRecord`, `DivergenceSummary`, `Snapshot` dataclasses with `to_dict()`/`from_dict()` and `to_json()`/`from_json()` serialization; `SNAPSHOT_VERSION = "0.1.0"`; null deltas on first snapshot
- **`src/sdi/snapshot/storage.py`**: `write_atomic()` (tempfile + `os.replace`, cleanup on failure), `write_snapshot()`, `read_snapshot()`, `list_snapshots()` (sorted chronologically by filename), `enforce_retention()` (deletes oldest when over limit; 0 = unlimited)
- **`tests/conftest.py`**: Shared fixtures: `sample_divergence`, `sample_snapshot`, `sample_feature_record`, `sample_config_dict`, `git_repo_dir`, `sdi_project_dir`
- **`tests/unit/test_config.py`**: 27 tests covering defaults, project config loading, env vars (SDI_LOG_LEVEL, SDI_WORKERS, SDI_SNAPSHOT_DIR, SDI_CONFIG_PATH, NO_COLOR), invalid TOML (exit code 2 + path in message), missing `expires` (exit code 2 + override name in message), expired override skip, valid override applied, unknown key deprecation warning
- **`tests/unit/test_snapshot_model.py`**: 15 tests covering FeatureRecord construction, DivergenceSummary null-first-snapshot, JSON round-trip, `snapshot_version` presence, nested serialization
- **`tests/unit/test_storage.py`**: 15 tests covering atomic write, crash safety (no partial file, no temp file residue), sorted listing, non-snapshot file filtering, retention enforcement, unlimited retention
- **`.gitignore`**: Added `.sdi/cache/` and dist/build patterns

## Root Cause (bugs only)
N/A — greenfield implementation. One bug was caught during smoke testing: `init_cmd.py` checked `config_path.exists()` AFTER writing the file (always True). Fixed to capture `already_initialized = config_path.exists()` before the write.

## Files Modified

| File | Status |
|------|--------|
| `pyproject.toml` | NEW |
| `src/sdi/__init__.py` | NEW |
| `src/sdi/config.py` | NEW |
| `src/sdi/cli/__init__.py` | NEW |
| `src/sdi/cli/init_cmd.py` | NEW |
| `src/sdi/snapshot/__init__.py` | NEW |
| `src/sdi/snapshot/model.py` | NEW |
| `src/sdi/snapshot/storage.py` | NEW |
| `tests/__init__.py` | NEW |
| `tests/conftest.py` | NEW |
| `tests/unit/__init__.py` | NEW |
| `tests/unit/test_config.py` | NEW |
| `tests/unit/test_snapshot_model.py` | NEW |
| `tests/unit/test_storage.py` | NEW |
| `.gitignore` | MODIFIED (added `.sdi/cache/`, `dist/`, `build/`) |

## Human Notes Status
No Human Notes section present in this task.

## Architecture Change Proposals

### FeatureRecord location: model.py vs parsing/__init__.py

- **Current constraint**: CLAUDE.md repository layout places `FeatureRecord` in `src/sdi/parsing/__init__.py`
- **What triggered this**: M01 milestone deliverables explicitly place it in `src/sdi/snapshot/model.py` as part of the core data structures foundation. The parsing module is M02.
- **Proposed change**: `FeatureRecord` is defined in `src/sdi/snapshot/model.py` for M01. M02 will re-export it from `sdi.parsing` to satisfy the CLAUDE.md layout contract.
- **Backward compatible**: Yes — the definition location is an implementation detail; callers import from `sdi.snapshot.model` or `sdi.snapshot` in M01, and M02 will add the re-export.
- **ARCHITECTURE.md update needed**: No — CLAUDE.md already notes this as a "Seeds Forward" decision in the M01 milestone.

### CoreConfig gains log_level and workers fields

- **Current constraint**: CLAUDE.md default config TOML shows no `log_level` or `workers` keys in `[core]`.
- **What triggered this**: `SDI_LOG_LEVEL` and `SDI_WORKERS` environment variables are documented in CLAUDE.md env var table. They need config fields to land in.
- **Proposed change**: Added `log_level: str = "WARNING"` and `workers: int = 0` to `CoreConfig`. These are also settable via `[core]` in `config.toml`.
- **Backward compatible**: Yes — both have safe defaults; existing config files without these keys are unaffected.
- **ARCHITECTURE.md update needed**: Yes — add `log_level` and `workers` to the `[core]` section of the complete default config table in CLAUDE.md.

## Observed Issues (out of scope)
None observed.
