## Planned Tests
- [x] `tests/unit/test_check_cmd.py` — expired threshold override does not raise threshold (CLAUDE.md rule 5)
- [x] `tests/integration/test_cli_output.py` — sdi diff with invalid ref_a and invalid ref_b each exit 1
- [x] `tests/integration/test_full_pipeline.py` — sdi trend --dimension filters to only requested dimension
- [x] `tests/unit/test_helpers.py` — resolve_snapshots_dir: path-traversal rejection raises SystemExit(2), happy path returns correct path
- [x] `tests/unit/test_boundaries_cmd.py` — display helpers and sub-operations for boundaries_cmd.py (M9 primary CLI behavior)
- [x] `tests/unit/test_delta.py` — add _count_boundary_violations tests for intent_divergence M9 addition
- [x] `tests/unit/test_assembly.py` — add _attach_intent_divergence happy path and fallback tests
- [x] `tests/unit/test_fingerprint_cache.py` — unit tests for all four public functions in sdi.patterns._fingerprint_cache (M10)
- [x] `tests/unit/test_assembly.py` — add _cleanup_caches integration path: orphan cleanup called with correct active_hashes (M10)

## Test Run Results
Passed: 654  Failed: 0

## Bugs Found
None

## Files Modified
- [x] `tests/unit/test_check_cmd.py`
- [x] `tests/integration/test_cli_output.py`
- [x] `tests/integration/test_full_pipeline.py`
- [x] `tests/unit/test_helpers.py`
- [x] `tests/unit/test_boundaries_cmd.py`
- [x] `tests/unit/test_delta.py`
- [x] `tests/unit/test_assembly.py`
- [x] `tests/unit/test_fingerprint_cache.py`
