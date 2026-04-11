## Planned Tests
- [x] `tests/unit/test_leiden_internals.py` — add _read_cache JSON-array coverage and _build_initial_membership missing-keys coverage

## Test Run Results
Passed: 22  Failed: 1

## Bugs Found
- BUG: [src/sdi/detection/_partition_cache.py:45] _read_cache raises AttributeError when partition.json contains a top-level JSON array (e.g. [1,2,3]) because AttributeError is not in the except tuple; stated contract is corrupt cache → cold start (return None)

## Files Modified
- [x] `tests/unit/test_leiden_internals.py`
