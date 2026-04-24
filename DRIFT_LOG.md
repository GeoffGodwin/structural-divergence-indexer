# Drift Log

## Metadata
- Last audit: never
- Runs since audit: 2

## Unresolved Observations
- [2026-04-23 | "Implement Milestone 8: CLI Commands — snapshot, show, diff, trend, check, catalog"] `src/sdi/cli/snapshot_cmd.py:46` — exception tuple `(FileNotFoundError, subprocess.TimeoutExpired)` in `_get_commit_sha` does not cover `PermissionError` (e.g., git binary not executable). Low-risk gap, not a blocker.
- [2026-04-23 | "Implement Milestone 8: CLI Commands — snapshot, show, diff, trend, check, catalog"] `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates; safe only if config layer pre-filters expired overrides. Pre-existing from prior cycle; not introduced by this change.
- [2026-04-23 | "Implement Milestone 8: CLI Commands — snapshot, show, diff, trend, check, catalog"] `_partition_cache.py:48` — `KeyError` in `except (json.JSONDecodeError, OSError, KeyError)` is dead after the `isinstance(data, dict)` guard. Carried from prior cycle.
- [2026-04-23 | "M08"] `_partition_cache.py:48` — `KeyError` in the `except (json.JSONDecodeError, OSError, KeyError)` clause is dead after the `isinstance(data, dict)` guard. The only remaining code in the try block uses `.get()` which does not raise `KeyError`. Misleading to future readers; could be trimmed to `except (json.JSONDecodeError, OSError)`.
- [2026-04-23 | "M08"] `diff_cmd.py:54-56` — the `_load_pair` docstring and Click help string are now accurate, but the behavior when `ref_a` is provided and `ref_b` is `None` silently resolves `ref_b` to "latest" via `resolve_snapshot_ref(snapshots_dir, None)`. This is now documented in the Click command help, which is correct. Observation only.

## Resolved
