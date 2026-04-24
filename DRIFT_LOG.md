# Drift Log

## Metadata
- Last audit: 2026-04-24
- Runs since audit: 1

## Unresolved Observations
- [2026-04-24 | "Address all 11 open non-blocking notes in NON_BLOCKING_LOG.md. Fix each item and note what you changed."] `init_cmd.py:232-233` — `list_snapshots`, `read_snapshot`, and `partition_to_proposed_yaml` are imported inside `_infer_boundaries_from_snapshot` as intentional deferred imports (best-effort, gracefully handled). This is correct and not a violation, but differs from the top-level import style used everywhere else. Future cleanup could consider whether these imports can be hoisted to module level now that the function is stable.

## Resolved
- [RESOLVED 2026-04-24] `setup_fixture.py:155`: Standalone default output path is `tests/fixtures/evolving` — the same directory as the static reference files. Running the script standalone would overwrite those files and create a git repo in their place. Consider defaulting to a temp path or adding a guard to prevent clobbering the reference files.
- [RESOLVED 2026-04-24] `init_cmd.py:229-230`: `from sdi.cli.boundaries_cmd import _partition_to_proposed_yaml` crosses an intra-CLI boundary via a private function. `_partition_to_proposed_yaml` is a pure formatting utility that belongs closer to `sdi.detection.boundaries` rather than buried in another CLI module.
- [RESOLVED 2026-04-24] `cli/__init__.py:30`: `signal.signal(signal.SIGTERM, _sigterm_handler)` executes at module import time as a side effect. Acceptable for a pure-CLI entry point, but any test that does `import sdi.cli` will silently install the SIGTERM handler — worth noting if the test suite ever needs to control signal disposition.
- [RESOLVED 2026-04-24] `assembly.py:158`, `snapshot_cmd.py:203`, and `_runner.py:152` each independently hardcode `repo_root / ".sdi" / "cache"`. Three sites for the same path with no shared constant. Centralizing as a helper or config attribute would reduce future update risk.
- [2026-04-24 | "Implement Milestone 12: Integration Tests, Polish, and Packaging"] `test_full_pipeline.py:21-54` and `test_multi_snapshot.py:36-49`: `_has_python_adapter()`, `_has_ts_adapter()`, and the `requires_python_adapter` mark are duplicated across both integration test files. These belong in `tests/conftest.py`. *(Resolved: All helpers now defined exclusively in `tests/conftest.py` and imported by both test files.)*
- [2026-04-24 | "Implement Milestone 12: Integration Tests, Polish, and Packaging"] `test_multi_snapshot.py:20-33`: `_latest_by_mtime` patches over a known limitation in `storage.list_snapshots` (alphabetical sort breaks on same-second filenames). If storage is ever fixed to sort by timestamp, this helper becomes dead weight. A `# TODO: remove once list_snapshots uses mtime` comment would track this. *(Resolved: TODO comment already present in docstring at `test_multi_snapshot.py:28`.)*
