# Drift Log

## Metadata
- Last audit: 2026-04-24
- Runs since audit: 3

## Unresolved Observations
- [2026-04-24 | "Implement Milestone 14: Shell Pattern Quality, Trend Calibration, and Rollout"] `categories.py:112-123` — `_SHELL_QUERIES = {}` is declared and then checked in `_build_registry` via `if name in _SHELL_QUERIES`. Since the dict is intentionally empty, this branch is permanently dead code. The comment explains the rationale (extraction lives in `_shell_patterns.py`), but the dead branch is misleading to future readers who might expect it to execute. Consider removing the branch entirely and leaving only the comment explaining the architecture decision.
- [2026-04-24 | "Implement Milestone 14: Shell Pattern Quality, Trend Calibration, and Rollout"] `shell.py` and `_shell_patterns.py` each contain private `_node_text` and `_get_command_name` functions with identical byte-for-byte implementations. This is a latent drift hazard: a future maintainer fixing one copy may not notice the other.
- [2026-04-24 | "M13"] `categories.py:112-123` — `_SHELL_QUERIES = {}` is declared and then checked in `_build_registry` via `if name in _SHELL_QUERIES`. Since the dict is intentionally empty, this branch is permanently dead code. The comment explains the rationale (extraction lives in `_shell_patterns.py`), but the dead branch is misleading to future readers who might expect it to execute. Consider removing the branch entirely and leaving only the comment explaining the architecture decision.
- [2026-04-24 | "M13"] `shell.py` and `_shell_patterns.py` each contain private `_node_text` and `_get_command_name` functions with identical byte-for-byte implementations. This is a latent drift hazard: a future maintainer fixing one copy may not notice the other.
- [2026-04-24 | "Address all 11 open non-blocking notes in NON_BLOCKING_LOG.md. Fix each item and note what you changed."] `init_cmd.py:232-233` — `list_snapshots`, `read_snapshot`, and `partition_to_proposed_yaml` are imported inside `_infer_boundaries_from_snapshot` as intentional deferred imports (best-effort, gracefully handled). This is correct and not a violation, but differs from the top-level import style used everywhere else. Future cleanup could consider whether these imports can be hoisted to module level now that the function is stable.

## Resolved
