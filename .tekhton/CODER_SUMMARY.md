# Coder Summary
## Status: COMPLETE

## What Was Implemented

### Fixes from M08 Reviewer Report

1. **Fixed pre-existing failing test** (`_partition_cache.py`): `_read_cache()` now guards against a top-level JSON array with an `isinstance(data, dict)` check before calling `.get()`. Fixes `test_read_cache_toplevel_array_returns_none`.

2. **Fixed lazy imports in `snapshot_cmd.py`**: Moved `emit_rows_csv` and `format_delta` from lazy inline imports inside `_print_snapshot_summary` to module-level imports, consistent with all other command files.

3. **Added `resolve_snapshots_dir()` to `_helpers.py`**: New helper that applies the same path bounds check as `assembly.py:127-130`, ensuring `snapshots_dir` stays within the repository root. Exits with code 2 if violated. Applied uniformly to all 6 CLI commands.

4. **Applied `resolve_snapshots_dir()` to all 6 CLI commands**: `snapshot_cmd`, `show_cmd`, `diff_cmd`, `trend_cmd`, `check_cmd`, `catalog_cmd` all now call `resolve_snapshots_dir()` instead of directly constructing `repo_root / config.snapshots.dir`.

5. **Documented implicit partial-ref behavior in `diff_cmd.py`**: Updated `_load_pair` docstring and Click command docstring to explicitly state that a `None` ref resolves to the latest snapshot, so `sdi diff A` diffs A against the latest.

## Root Cause (bugs only)
- `_partition_cache.py:45`: `json.load()` can return any JSON value (list, str, etc.), but the code called `.get()` on the result assuming it was always a dict. `isinstance(data, dict)` guard was missing.

## Files Modified
- `src/sdi/detection/_partition_cache.py` — Added `isinstance(data, dict)` guard in `_read_cache()`
- `src/sdi/cli/_helpers.py` — Added `resolve_snapshots_dir()` helper function
- `src/sdi/cli/snapshot_cmd.py` — Moved lazy imports to module level; use `resolve_snapshots_dir()`
- `src/sdi/cli/show_cmd.py` — Use `resolve_snapshots_dir()`
- `src/sdi/cli/diff_cmd.py` — Use `resolve_snapshots_dir()`; documented partial-ref behavior
- `src/sdi/cli/trend_cmd.py` — Use `resolve_snapshots_dir()`
- `src/sdi/cli/check_cmd.py` — Use `resolve_snapshots_dir()`
- `src/sdi/cli/catalog_cmd.py` — Use `resolve_snapshots_dir()`

## Human Notes Status
No Human Notes section present.

## Docs Updated
None — no public-surface changes in this task.

## Observed Issues (out of scope)
- `tests/conftest.py:168` — `run_sdi` uses `os.chdir()` which is process-wide state. Potential race if tests are ever parallelized with pytest-xdist. Pre-existing non-blocking issue; not addressed per scope adherence.
- `src/sdi/cli/init_cmd.py:21,122` — Two E501 (line too long) ruff violations. Pre-existing, not introduced by this run.
