# Reviewer Report — M08 Cycle 2 (re-review)

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- None

## Coverage Gaps
- `_helpers.py:resolve_snapshots_dir` — no unit test for the path-traversal rejection case (e.g., `config.snapshots.dir = "../../etc"`). This is the security-relevant branch introduced by M08 and should have a test asserting `SystemExit(2)` is raised when the resolved path escapes the repo root. (Carried from prior cycle.)
- `tests/unit/test_check_cmd.py` — no test for an expired threshold override (pre-existing gap; not introduced by M08). (Carried from prior cycle.)

## Drift Observations
- `src/sdi/cli/snapshot_cmd.py:46` — exception tuple `(FileNotFoundError, subprocess.TimeoutExpired)` in `_get_commit_sha` does not cover `PermissionError` (e.g., git binary not executable). Low-risk gap, not a blocker.
- `check_cmd.py:70-73` — `_effective_threshold` applies overrides without checking expiry dates; safe only if config layer pre-filters expired overrides. Pre-existing from prior cycle; not introduced by this change.
- `_partition_cache.py:48` — `KeyError` in `except (json.JSONDecodeError, OSError, KeyError)` is dead after the `isinstance(data, dict)` guard. Carried from prior cycle.

## Prior Blocker Resolution

- **FIXED** — `src/sdi/cli/snapshot_cmd.py`: `import json` is now in the contiguous stdlib imports block at line 5, alongside `import subprocess`, `from datetime import ...`, `from pathlib import ...`, and `from typing import ...`. No extraneous blank line separating it from the stdlib group. Blocker is resolved.
