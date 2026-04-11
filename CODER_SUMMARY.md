# Coder Summary
## Status: COMPLETE

## What Was Implemented

### CLI Commands (Milestone 8)
- **`sdi snapshot`** — Full 5-stage pipeline (parse → graph → detect → catalog → assemble). Gracefully degrades if igraph/leidenalg are unavailable. Progress messages go to stderr; data goes to stdout. Supports `--format text/json/csv`.
- **`sdi show [REF]`** — Display snapshot details (divergence summary, graph metrics, community detection). Supports integer index, negative index, and filename-prefix references. Defaults to latest.
- **`sdi diff [A] [B]`** — Compare two snapshots (defaults to last two). Recomputes delta of B relative to A using `compute_delta()`. All output formats supported.
- **`sdi trend`** — Time-series output across snapshots. Supports `--last N` and `--dimension` (repeatable). Validates dimension names against `ALL_DIMENSIONS`.
- **`sdi check [REF]`** — Threshold gate. Compares delta fields against configured thresholds with override support. Exits 10 on breach, 0 on OK. Null deltas (first snapshot) are never a breach.
- **`sdi catalog [REF]`** — Display pattern catalog from a snapshot. Shows categories, entropy, canonical hash, shape stats (instances/velocity/spread/files).
- **`boundaries` placeholder** — Retained for Milestone 9.

### Shared Infrastructure
- **`src/sdi/cli/_helpers.py`** — Shared helpers: `find_git_root`, `require_initialized`, `resolve_snapshot_ref`, `load_snapshot_by_ref`, `format_delta`, `emit_json`, `emit_rows_csv`.
- **Updated `src/sdi/cli/__init__.py`** — Replaced placeholder commands with real implementations, restored `boundaries` placeholder for M09.

### Tests
- **`tests/unit/test_check_cmd.py`** — 14 unit tests for `run_checks()` and threshold override logic.
- **`tests/integration/test_cli_output.py`** — 16 integration tests for all commands' output formats (text/json/csv) and exit codes.
- **`tests/integration/test_full_pipeline.py`** — 9 end-to-end tests: init → snapshot → show → catalog → check → diff → trend workflow. Uses `@pytest.mark.skipif` when Python tree-sitter adapter unavailable.
- **Updated `tests/conftest.py`** — Added `cli_runner`, `run_sdi`, and `sdi_project_with_snapshot` fixtures.

## Root Cause (bugs only)
N/A — feature implementation

## Files Modified
- `src/sdi/cli/_helpers.py` (NEW) — Shared helper utilities
- `src/sdi/cli/snapshot_cmd.py` (NEW) — `sdi snapshot` command
- `src/sdi/cli/show_cmd.py` (NEW) — `sdi show` command
- `src/sdi/cli/diff_cmd.py` (NEW) — `sdi diff` command
- `src/sdi/cli/trend_cmd.py` (NEW) — `sdi trend` command
- `src/sdi/cli/check_cmd.py` (NEW) — `sdi check` command
- `src/sdi/cli/catalog_cmd.py` (NEW) — `sdi catalog` command
- `src/sdi/cli/__init__.py` (MODIFIED) — Registered real commands, restored boundaries placeholder
- `tests/unit/test_check_cmd.py` (NEW) — Threshold logic unit tests
- `tests/integration/test_cli_output.py` (NEW) — CLI output format/exit code integration tests
- `tests/integration/test_full_pipeline.py` (NEW) — End-to-end pipeline integration tests
- `tests/conftest.py` (MODIFIED) — Added CLI runner fixtures

## Human Notes Status
No Human Notes section present.

## Architecture Change Proposals
None — implementation follows the architecture described in CLAUDE.md exactly.

## Observed Issues (out of scope)
- `src/sdi/detection/_partition_cache.py:45` — `_read_cache()` doesn't guard against a top-level JSON array (calls `.get()` on a list), causing `AttributeError`. Covered by `tests/unit/test_leiden_internals.py::test_read_cache_toplevel_array_returns_none` which fails. Pre-existing, not introduced by M08.
- `src/sdi/cli/init_cmd.py:21,122` — Two E501 (line too long) ruff violations. Pre-existing.
- `tests/conftest.py:25,109` — Two E501 ruff violations in pre-existing docstrings. Pre-existing.
