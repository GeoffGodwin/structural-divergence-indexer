## Planned Tests
- [x] `tests/integration/test_completion_cmd.py` — verify `sdi completion bash/zsh/fish` emits eval line to stdout and hint to stderr, exits 0; invalid shell exits non-zero
- [x] `tests/unit/test_init_cmd.py` — verify `_maybe_install_hooks` TTY-prompt branch installs correct hooks based on confirm responses; verify `_infer_boundaries_from_snapshot` success and fallback paths
- [x] `tests/conftest.py` — Consolidate adapter detection helpers and pytest marks (dedup from test files)
- [x] `tests/integration/test_full_pipeline.py` — Fix except clauses, remove duplicated helpers, add TestInitAndSnapshot (sdi init → snapshot path)
- [x] `tests/integration/test_multi_snapshot.py` — Fix except clause, add _latest_by_mtime empty-list guard + TODO comment, add config-ordering comment, add TestBoundariesCommand (sdi boundaries with/without spec, propose after snapshot)

## Test Run Results
Passed: 774  Failed: 0

## Bugs Found
None

## Files Modified
- [x] `tests/integration/test_completion_cmd.py`
- [x] `tests/unit/test_init_cmd.py`
- [x] `tests/conftest.py`
- [x] `tests/integration/test_full_pipeline.py`
- [x] `tests/integration/test_multi_snapshot.py`
