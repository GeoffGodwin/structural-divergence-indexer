# Drift Log

## Metadata
- Last audit: never
- Runs since audit: 1

## Unresolved Observations
- [2026-04-23 | "M08"] `_partition_cache.py:48` — `KeyError` in the `except (json.JSONDecodeError, OSError, KeyError)` clause is dead after the `isinstance(data, dict)` guard. The only remaining code in the try block uses `.get()` which does not raise `KeyError`. Misleading to future readers; could be trimmed to `except (json.JSONDecodeError, OSError)`.
- [2026-04-23 | "M08"] `diff_cmd.py:54-56` — the `_load_pair` docstring and Click help string are now accurate, but the behavior when `ref_a` is provided and `ref_b` is `None` silently resolves `ref_b` to "latest" via `resolve_snapshot_ref(snapshots_dir, None)`. This is now documented in the Click command help, which is correct. Observation only.

## Resolved
