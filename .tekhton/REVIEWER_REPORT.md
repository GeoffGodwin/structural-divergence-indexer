# Reviewer Report — M13: Shell Language Discovery and Adapter Foundation

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `_node_text` and `_get_command_name` are privately defined in both `shell.py` and `_shell_patterns.py` with identical implementations. Since `_shell_patterns.py` is already imported by `shell.py`, one could import from the other to avoid the duplication. Current state is harmless but creates a drift risk if one copy is later updated.

## Coverage Gaps
- `TestShellErrorHandling` covers `set`, `trap`, and `exit/return` forms but not the `||/&&` list bail pattern (e.g., `cmd || exit 1`). The coder summary explicitly lists `||/&&` list nodes as a detected shape, and the implementation in `_check_list_node` handles it, but there is no unit test exercising this code path. The integration fixture (`deploy.sh` line 17: `do_deploy "${env}" || exit 1`) exercises it indirectly, but the integration test only asserts that `error_handling` is present in categories — it does not isolate the `||` path.

## Drift Observations
- `categories.py:112-123` — `_SHELL_QUERIES = {}` is declared and then checked in `_build_registry` via `if name in _SHELL_QUERIES`. Since the dict is intentionally empty, this branch is permanently dead code. The comment explains the rationale (extraction lives in `_shell_patterns.py`), but the dead branch is misleading to future readers who might expect it to execute. Consider removing the branch entirely and leaving only the comment explaining the architecture decision.
- `shell.py` and `_shell_patterns.py` each contain private `_node_text` and `_get_command_name` functions with identical byte-for-byte implementations. This is a latent drift hazard: a future maintainer fixing one copy may not notice the other.
