# Drift Log

## Metadata
- Last audit: 2026-04-24
- Runs since audit: 1

## Unresolved Observations
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `assembly.py:158`, `snapshot_cmd.py:203`, and `_runner.py:152` each independently hardcode `repo_root / ".sdi" / "cache"`. Three sites for the same path with no shared constant. Centralizing as a helper or config attribute would reduce future update risk.
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `DRIFT_LOG.md` pre-existing: the unresolved `diff_cmd.py:54-56` observation (noted by the coder as out of scope) should be moved to Resolved in the next housekeeping pass.
- [2026-04-24 | "architect audit"] `diff_cmd.py:54-56` `[2026-04-23 | "M08"]` — Observation only. The previous audit cycle recommended raising an error for partial spec; instead, the behavior was documented in the Click command help string ("With only SNAPSHOT_A, diffs A against the latest snapshot."). The observation explicitly labels itself "Observation only" and notes the help string is now accurate. No code change is warranted. Remove from DRIFT_LOG.md as resolved-by-documentation.

## Resolved
- [RESOLVED 2026-04-24] `src/sdi/cli/snapshot_cmd.py:46` — exception tuple `(FileNotFoundError, subprocess.TimeoutExpired)` in `_get_commit_sha` does not cover `PermissionError` (e.g., git binary not executable). Low-risk gap, not a blocker.
- [RESOLVED 2026-04-24] `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates; safe only if config layer pre-filters expired overrides. Pre-existing from prior cycle; not introduced by this change.
- [RESOLVED 2026-04-24] `_partition_cache.py:48` — `KeyError` in `except (json.JSONDecodeError, OSError, KeyError)` is dead after the `isinstance(data, dict)` guard. Carried from prior cycle.
- [RESOLVED 2026-04-24] `src/sdi/cli/snapshot_cmd.py:46` — exception tuple `(FileNotFoundError, subprocess.TimeoutExpired)` in `_get_commit_sha` does not cover `PermissionError` (e.g., git binary not executable). Low-risk gap, not a blocker.
- [RESOLVED 2026-04-24] `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates; safe only if config layer pre-filters expired overrides. Pre-existing from prior cycle; not introduced by this change.
- [RESOLVED 2026-04-24] `_partition_cache.py:48` — `KeyError` in `except (json.JSONDecodeError, OSError, KeyError)` is dead after the `isinstance(data, dict)` guard. Carried from prior cycle.
- [RESOLVED 2026-04-24] `_partition_cache.py:48` — `KeyError` in the `except (json.JSONDecodeError, OSError, KeyError)` clause is dead after the `isinstance(data, dict)` guard. The only remaining code in the try block uses `.get()` which does not raise `KeyError`. Misleading to future readers; could be trimmed to `except (json.JSONDecodeError, OSError)`.
- [RESOLVED 2026-04-24] `diff_cmd.py:54-56` — the `_load_pair` docstring and Click help string are now accurate, but the behavior when `ref_a` is provided and `ref_b` is `None` silently resolves `ref_b` to "latest" via `resolve_snapshot_ref(snapshots_dir, None)`. This is now documented in the Click command help, which is correct. Observation only.
