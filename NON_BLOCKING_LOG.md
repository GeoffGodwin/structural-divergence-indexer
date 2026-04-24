# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in ${REVIEWER_REPORT_FILE}.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-23 | "M08"] `snapshot_cmd.py:124` — `import json` remains as an inline import inside `_print_snapshot_summary`. The task correctly moved `emit_rows_csv` and `format_delta` to module level, but this stdlib import was left in place. Harmless (stdlib, always available), but inconsistent with the now-clean import style of the rest of the file. Pre-existing; can be addressed in cleanup.
- [ ] [2026-04-23 | "M08"] `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates. CLAUDE.md rule 5 mandates stale overrides resume default thresholds after expiry. This is safe only if the config layer pre-filters expired overrides before they appear in `thresholds.overrides`. This concern is pre-existing and not introduced by M08; noting for tracking.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
