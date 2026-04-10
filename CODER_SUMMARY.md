# Coder Summary
## Status: COMPLETE

## What Was Implemented

All Milestone 2 deliverables were already implemented by the prior run. This continuation
run verified correctness, fixed two issues, and confirmed all tests pass.

**Core implementation (completed in prior run):**
- `src/sdi/parsing/__init__.py` — public API re-exporting `parse_repository`, `FeatureRecord`, `LanguageAdapter`, `discover_files`, `detect_language`
- `src/sdi/parsing/discovery.py` — file tree walking with `.gitignore` filtering (via `pathspec`), configurable exclude patterns, language detection by extension
- `src/sdi/parsing/base.py` — `LanguageAdapter` ABC with `language_name`, `file_extensions`, `parse_file`, and `parse_file_safe` interface
- `src/sdi/parsing/python.py` — Python tree-sitter adapter: import extraction (regular, from-, relative), symbol extraction (functions, classes, top-level constants, decorated definitions), CST discarded before return
- `src/sdi/parsing/_python_patterns.py` — pattern instance extraction (try/except → `error_handling`, logging calls → `logging`, ORM-like calls → `data_access`), structural AST hashing, LOC counting
- `src/sdi/parsing/_runner.py` — `parse_repository()` orchestrator: `ProcessPoolExecutor` parallelism, `SDI_WORKERS` env var support, missing-grammar warnings, exit-3 on all-missing
- `tests/fixtures/simple-python/` — 9 Python files with known import graph, cross-module dependencies, try/except and logging patterns
- `tests/unit/test_discovery.py` — 24 tests covering language detection, `.gitignore`, exclude patterns, `.git` exclusion, nested dirs
- `tests/unit/test_python_adapter.py` — 36 tests covering imports, symbols, pattern instances, FeatureRecord metadata, LOC counting

**Fixes applied in this run:**
- Added `pathspec>=0.11` to `pyproject.toml` required dependencies (was used but not declared)
- Changed `pathspec.PathSpec.from_lines("gitwildmatch", ...)` → `"gitignore"` in `discovery.py` to eliminate deprecation warnings

## Root Cause (bugs only)
N/A — feature implementation

## Files Modified
- `pyproject.toml` — added `pathspec>=0.11` to required dependencies
- `src/sdi/parsing/discovery.py` — fixed pathspec pattern name `gitwildmatch` → `gitignore`

## Human Notes Status
No human notes present in this milestone.

## Observed Issues (out of scope)
- `tests/conftest.py:55` — `sample_feature_record` fixture uses `pattern_instances` dict with `"type"` key but the actual schema uses `"category"`, `"ast_hash"`, `"location"`. This may cause failures in future tests that validate pattern_instances shape. Not fixed here as no current test depends on it.
