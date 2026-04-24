# Reviewer Report — M08 (Cycle 1)

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `snapshot_cmd.py:124` — `import json` remains as an inline import inside `_print_snapshot_summary`. The task correctly moved `emit_rows_csv` and `format_delta` to module level, but this stdlib import was left in place. Harmless (stdlib, always available), but inconsistent with the now-clean import style of the rest of the file. Pre-existing; can be addressed in cleanup.
- `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates. CLAUDE.md rule 5 mandates stale overrides resume default thresholds after expiry. This is safe only if the config layer pre-filters expired overrides before they appear in `thresholds.overrides`. This concern is pre-existing and not introduced by M08; noting for tracking.

## Coverage Gaps
- `_helpers.py:resolve_snapshots_dir` — no unit test for the path-traversal rejection case (e.g., `config.snapshots.dir = "../../etc"`). This is the security-relevant branch introduced by M08 and should have a test asserting `SystemExit(2)` is raised when the resolved path escapes the repo root.
- `tests/unit/test_check_cmd.py` — no test for an expired threshold override (pre-existing gap; not introduced by M08, but flagged here to track).

## Drift Observations
- `_partition_cache.py:48` — `KeyError` in the `except (json.JSONDecodeError, OSError, KeyError)` clause is dead after the `isinstance(data, dict)` guard. The only remaining code in the try block uses `.get()` which does not raise `KeyError`. Misleading to future readers; could be trimmed to `except (json.JSONDecodeError, OSError)`.
- `diff_cmd.py:54-56` — the `_load_pair` docstring and Click help string are now accurate, but the behavior when `ref_a` is provided and `ref_b` is `None` silently resolves `ref_b` to "latest" via `resolve_snapshot_ref(snapshots_dir, None)`. This is now documented in the Click command help, which is correct. Observation only.
