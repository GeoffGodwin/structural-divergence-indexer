# Drift Log

## Metadata
- Last audit: 2026-04-24
- Runs since audit: 3

## Unresolved Observations
- [2026-04-24 | "Implement Milestone 12: Integration Tests, Polish, and Packaging"] `test_full_pipeline.py:21-54` and `test_multi_snapshot.py:36-49`: `_has_python_adapter()`, `_has_ts_adapter()`, and the `requires_python_adapter` mark are duplicated across both integration test files. These belong in `tests/conftest.py`.
- [2026-04-24 | "Implement Milestone 12: Integration Tests, Polish, and Packaging"] `test_multi_snapshot.py:20-33`: `_latest_by_mtime` patches over a known limitation in `storage.list_snapshots` (alphabetical sort breaks on same-second filenames). If storage is ever fixed to sort by timestamp, this helper becomes dead weight. A `# TODO: remove once list_snapshots uses mtime` comment would track this.
- [2026-04-24 | "Implement Milestone 12: Integration Tests, Polish, and Packaging"] `setup_fixture.py:155`: Standalone default output path is `tests/fixtures/evolving` — the same directory as the static reference files. Running the script standalone would overwrite those files and create a git repo in their place. Consider defaulting to a temp path or adding a guard to prevent clobbering the reference files.
- [2026-04-24 | "M11"] `init_cmd.py:229-230`: `from sdi.cli.boundaries_cmd import _partition_to_proposed_yaml` crosses an intra-CLI boundary via a private function. `_partition_to_proposed_yaml` is a pure formatting utility that belongs closer to `sdi.detection.boundaries` rather than buried in another CLI module.
- [2026-04-24 | "M11"] `cli/__init__.py:30`: `signal.signal(signal.SIGTERM, _sigterm_handler)` executes at module import time as a side effect. Acceptable for a pure-CLI entry point, but any test that does `import sdi.cli` will silently install the SIGTERM handler — worth noting if the test suite ever needs to control signal disposition.
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `assembly.py:158`, `snapshot_cmd.py:203`, and `_runner.py:152` each independently hardcode `repo_root / ".sdi" / "cache"`. Three sites for the same path with no shared constant. Centralizing as a helper or config attribute would reduce future update risk.
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `DRIFT_LOG.md` pre-existing: the unresolved `diff_cmd.py:54-56` observation (noted by the coder as out of scope) should be moved to Resolved in the next housekeeping pass.
- [2026-04-24 | "architect audit"] `diff_cmd.py:54-56` `[2026-04-23 | "M08"]` — Observation only. The previous audit cycle recommended raising an error for partial spec; instead, the behavior was documented in the Click command help string ("With only SNAPSHOT_A, diffs A against the latest snapshot."). The observation explicitly labels itself "Observation only" and notes the help string is now accurate. No code change is warranted. Remove from DRIFT_LOG.md as resolved-by-documentation.

## Resolved
