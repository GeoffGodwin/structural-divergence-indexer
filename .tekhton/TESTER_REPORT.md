## Planned Tests
- [x] `tests/integration/test_completion_cmd.py` — verify `sdi completion bash/zsh/fish` emits eval line to stdout and hint to stderr, exits 0; invalid shell exits non-zero
- [x] `tests/unit/test_init_cmd.py` — verify `_maybe_install_hooks` TTY-prompt branch installs correct hooks based on confirm responses; verify `_infer_boundaries_from_snapshot` success and fallback paths

## Test Run Results
Passed: 739  Failed: 0

## Bugs Found
None

## Files Modified
- [x] `tests/integration/test_completion_cmd.py`
- [x] `tests/unit/test_init_cmd.py`
