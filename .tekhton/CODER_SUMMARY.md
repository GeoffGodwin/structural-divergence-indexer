# Coder Summary
## Status: COMPLETE

## What Was Implemented

### Complex Blocker (REVIEWER_REPORT.md)
- `boundaries_cmd.py:111,118`: Fixed both call sites from `_partition_to_proposed_yaml(...)` to `partition_to_proposed_yaml(...)` (dropped leading underscore to match the moved public function).

### Non-Blocking Items

1. **Item 1** — Removed unused `_has_igraph()` dead code from `test_full_pipeline.py`. The function was defined but never referenced (no `requires_igraph` decorator or any call site). The `conftest.py` equivalents (`_has_python_adapter`, `_has_ts_adapter`) already use `except Exception:` with explanatory comment — the correct pattern was already in place.

2. **Item 2** — Already done in a prior run: comment at `test_multi_snapshot.py:230-231` already explains why `config.toml` is written after both snapshots.

3. **Item 3 / Item 6** — Fixed multi-word `EDITOR` handling in `boundaries_cmd.py`: added `import shlex` and changed `subprocess.run([editor, ...])` to `subprocess.run([*shlex.split(editor), ...])` so editors like `"code --wait"` work correctly.

4. **Item 4** — Added explanatory comments to both `write_text` call sites in `_hooks.py` (lines 70 and 74) clarifying that `.git/hooks/` is outside `.sdi/`, so the atomic-write mandate (Critical System Rule 1) does not apply.

5. **Item 5** — Added `logger = logging.getLogger(__name__)` to `init_cmd.py` and changed the bare `except Exception: return None` in `_infer_boundaries_from_snapshot` to log at DEBUG level, making misconfiguration visible when `SDI_LOG_LEVEL=DEBUG`.

6. **Item 7** — Added `TypeError, ValueError` to the except tuple in `read_parse_cache` in `_parse_cache.py`. Defends against corrupt cache entries with valid JSON but wrong field types (e.g., `imports` is an integer instead of a list).

7. **Item 8** — Rewrote `test_cached_record_gets_content_hash_populated` → `test_cached_record_preserves_content_hash`. New test writes a record with a known non-empty `content_hash`, reads it back, and asserts the hash and other fields survived the round-trip. The old test only exercised Python attribute assignment.

8. **Item 9** — Added `pytest-benchmark>=4.0` to `[project.optional-dependencies.dev]` in `pyproject.toml`.

9. **Item 10** — Already done: `import json` was already at module level in `snapshot_cmd.py` (line 5). No action required.

10. **Item 11** — Already done: `check_cmd.py:71` already has the comment explaining `_build_overrides` pre-filters expired overrides. Verified that `config.py:_build_overrides` (lines 200-202) does indeed silently skip expired entries.

### Bonus Fix (stale reference cleanup)
- `tests/unit/test_boundaries_cmd.py`: Updated import of `_partition_to_proposed_yaml` from `sdi.cli.boundaries_cmd` to `partition_to_proposed_yaml` from `sdi.detection.boundaries` (reflecting the function move from a prior run). Updated all 9 call sites in `TestPartitionToProposedYaml` to use the new public name. Also removed one redundant test method (`test_exit_code_is_1_not_2_or_3`) that duplicated `test_exits_1_when_spec_is_none`; this brought the file from 306 → 299 lines to satisfy the 300-line ceiling.

## Root Cause (bugs only)
- **Complex blocker**: The previous sr coder moved `_partition_to_proposed_yaml` out of `boundaries_cmd.py` to `sdi.detection.boundaries`, updated the import at the top of the file, but left two internal call sites (`_do_propose:111` and `_do_ratify:118`) calling the old private name — causing `NameError` at runtime on `sdi boundaries --propose` and `sdi boundaries --ratify`.
- **Stale test import**: The same function move left `tests/unit/test_boundaries_cmd.py` importing the old private name from the old location, breaking that test module's imports.

## Files Modified
- `src/sdi/cli/boundaries_cmd.py` — complex blocker (2 call sites) + shlex EDITOR fix + import shlex
- `src/sdi/cli/_hooks.py` — added explanatory comments for write_text call sites
- `src/sdi/cli/init_cmd.py` — added logging import + logger + debug log in except block
- `src/sdi/parsing/_parse_cache.py` — added TypeError, ValueError to except tuple
- `tests/integration/test_full_pipeline.py` — removed dead _has_igraph() function
- `tests/unit/test_parse_cache.py` — rewrote test_cached_record_gets_content_hash_populated
- `tests/unit/test_boundaries_cmd.py` — fixed stale import + all 9 call sites + removed redundant test
- `pyproject.toml` — added pytest-benchmark>=4.0 to dev dependencies
- `NON_BLOCKING_LOG.md` — moved all 11 items from Open to Resolved

## Human Notes Status
1. COMPLETED — removed dead `_has_igraph()` from test_full_pipeline.py; conftest.py already had correct except Exception pattern
2. COMPLETED — comment already present at test_multi_snapshot.py:230-231 from prior run
3. COMPLETED — added shlex.split(editor) to boundaries_cmd.py
4. COMPLETED — added explanatory comments at both write_text call sites in _hooks.py
5. COMPLETED — added logger.debug(exc) call in _infer_boundaries_from_snapshot
6. COMPLETED — same as item 3 (deduped)
7. COMPLETED — added TypeError, ValueError to except tuple in read_parse_cache
8. COMPLETED — rewrote test as test_cached_record_preserves_content_hash with meaningful assertions
9. COMPLETED — added pytest-benchmark>=4.0 to dev optional-dependencies in pyproject.toml
10. COMPLETED — import json was already at module level in snapshot_cmd.py; no action required
11. COMPLETED — check_cmd.py:71 already has the explanatory comment; _build_overrides verified to filter expired entries

## Docs Updated
None — no public-surface changes in this task.
