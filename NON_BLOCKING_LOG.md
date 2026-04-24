# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in ${REVIEWER_REPORT_FILE}.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [x] [2026-04-24 | "M13"] `_node_text` and `_get_command_name` are privately defined in both `shell.py` and `_shell_patterns.py` with identical implementations. Since `_shell_patterns.py` is already imported by `shell.py`, one could import from the other to avoid the duplication. Current state is harmless but creates a drift risk if one copy is later updated.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
