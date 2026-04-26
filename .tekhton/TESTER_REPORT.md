## Planned Tests
- [x] `tests/unit/test_js_ts_resolver.py` — unit tests for untested functions (_is_js_ts_file, _normalize_js_path, _build_js_path_set, _expand_alias_candidates) plus M18 bug-fix regression for @/* alias corruption
- [x] `tests/integration/test_validation_real_repos.py` — add warnings.warn to _run_snapshot for unexpected init exit codes (coverage gap from reviewer)

## Test Run Results
Passed: 45  Failed: 0

## Bugs Found
None

## Files Modified
- [x] `tests/unit/test_js_ts_resolver.py`
- [x] `tests/integration/test_validation_real_repos.py`
