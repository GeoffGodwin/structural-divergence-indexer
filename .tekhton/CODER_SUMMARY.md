# Coder Summary
## Status: COMPLETE

## What Was Implemented
- Added `scope_exclude: list[str]` to `PatternsConfig` with validation
- Extracted `_warn_unknown_keys` + new `_validate_scope_exclude` to `src/sdi/_config_scope.py` (to keep config.py under 300 lines)
- Filtering logic in `build_pattern_catalog` via pathspec — Stage 4 only
- `meta.scope_excluded_file_count` added to `PatternCatalog.to_dict()` when > 0
- `scope_exclude` added to `_compute_config_hash` in assembly.py
- Informational note in `sdi show` text output when files are excluded
- New fixture `tests/fixtures/scope-exclude-python/` with 5 structurally distinct patterns
- Unit tests for config validation and catalog filtering
- Integration tests for full pipeline and CLI output
- CLI output tests asserting the exclusion note appears/is absent per milestone spec

## Root Cause (bugs only)
N/A — feature milestone

## Files Modified
- `src/sdi/_config_scope.py` (NEW) — private validation helpers extracted from config.py
- `src/sdi/config.py` — added scope_exclude field to PatternsConfig; imports from _config_scope
- `src/sdi/patterns/catalog.py` — scope filtering + meta field
- `src/sdi/snapshot/assembly.py` — scope_exclude in config hash
- `src/sdi/cli/show_cmd.py` — informational note for excluded files
- `tests/fixtures/scope-exclude-python/` (NEW directory + 5 files)
- `tests/unit/test_config.py` — scope_exclude validation tests
- `tests/unit/test_catalog_scope.py` (NEW) — scope_exclude catalog tests
- `tests/integration/test_scope_exclude.py` (NEW) — integration tests
- `tests/integration/test_cli_output.py` — scope_excluded note tests (present/absent)
- `docs/ci-integration.md` — new subsection
- `CHANGELOG.md` — new entry
- `CLAUDE.md` — updated [patterns] default config block

## Human Notes Status
N/A — no Human Notes section in this task

## Docs Updated
- `docs/ci-integration.md` — added "Excluding test directories from the pattern catalog" subsection
- `CLAUDE.md` — updated `[patterns]` default config block with `scope_exclude = []`

## Architecture Change Proposals

### Extraction of `_warn_unknown_keys` + new validation to `src/sdi/_config_scope.py`
- **Current constraint**: `sdi/config.py` is described as "a leaf dependency — depended on by all modules, depends on none"
- **What triggered this**: config.py was at 304 lines before M17; adding 16 lines of scope_exclude logic would push it to 320 — violating the 300-line hard ceiling in coder.md
- **Proposed change**: Created `src/sdi/_config_scope.py` as a private helper containing `_warn_unknown_keys` (moved from config.py) and `_validate_scope_exclude` (new). config.py imports both from it. `_config_scope.py` has no SDI module dependencies (only stdlib + lazy pathspec import), so no circular dependency is introduced.
- **Backward compatible**: Yes — `_warn_unknown_keys` was a private function; nothing outside config.py called it. The public API of config.py is unchanged.
- **ARCHITECTURE.md update needed**: Yes — note that `_config_scope.py` is a private helper for config.py only; nothing else should import from it

## Design Observations
- The milestone spec says "invalid glob entries (e.g., `[unclosed`) raise `SystemExit(2)`", but pathspec/gitwildmatch semantics treat all strings as valid gitignore entries — `[unclosed` is silently treated as a literal pattern. The implementation validates non-string entries only, which is correct per pathspec's behavior. The docstring in `_validate_scope_exclude` documents this decision explicitly.
