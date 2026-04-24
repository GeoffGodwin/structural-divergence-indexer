# Reviewer Report — Milestone 12: Integration Tests, Polish, and Packaging

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `test_full_pipeline.py:28` and `test_multi_snapshot.py:42`: `except (ImportError, Exception)` is equivalent to bare `except Exception` since `Exception` is a superclass of `ImportError`. Drop the redundant `ImportError` and add a brief comment explaining why the broad catch is intentional (grammar init can raise OSError, RuntimeError, etc. depending on the tree-sitter backend).
- `test_multi_snapshot.py:223-248`: `config.toml` is written after both snapshots in `test_check_tight_thresholds_exits_10`. This is functionally correct (thresholds are only read by `sdi check`, not at snapshot time) but the ordering is non-obvious. A short inline comment would help future readers understand the intent.
- `ci.yml` has no pip dependency caching. Not a correctness issue, but the 3×3 matrix re-downloads and reinstalls on every run. Adding `cache: pip` to `actions/setup-python` is a low-effort improvement worth considering.
- Security finding from security agent (`boundaries_cmd.py:166` — multi-word EDITOR not split via shlex) is marked NOT_ADDRESSED in the coder summary as out of scope for M12. Confirmed low severity; acceptable to defer.

## Coverage Gaps
- `evolving_project` fixture manually creates `.sdi/` and `.sdi/snapshots/` rather than invoking `sdi init`. The `sdi init` command is not exercised by the multi-snapshot lifecycle tests. A test covering the actual `init → snapshot` path would close this gap.
- `_latest_by_mtime` has no guard against an empty snapshot list — `max()` on an empty sequence raises `ValueError`. If called before any snapshots exist the error message will be confusing rather than diagnostic.
- No test covers the `sdi boundaries` command path in the context of the multi-snapshot lifecycle (with or without a boundaries spec file).

## Drift Observations
- `test_full_pipeline.py:21-54` and `test_multi_snapshot.py:36-49`: `_has_python_adapter()`, `_has_ts_adapter()`, and the `requires_python_adapter` mark are duplicated across both integration test files. These belong in `tests/conftest.py`.
- `test_multi_snapshot.py:20-33`: `_latest_by_mtime` patches over a known limitation in `storage.list_snapshots` (alphabetical sort breaks on same-second filenames). If storage is ever fixed to sort by timestamp, this helper becomes dead weight. A `# TODO: remove once list_snapshots uses mtime` comment would track this.
- `setup_fixture.py:155`: Standalone default output path is `tests/fixtures/evolving` — the same directory as the static reference files. Running the script standalone would overwrite those files and create a git repo in their place. Consider defaulting to a temp path or adding a guard to prevent clobbering the reference files.
