# Drift Log

## Metadata
- Last audit: 2026-04-24
- Runs since audit: 2

## Unresolved Observations
- [2026-04-24 | "M11"] `init_cmd.py:229-230`: `from sdi.cli.boundaries_cmd import _partition_to_proposed_yaml` crosses an intra-CLI boundary via a private function. `_partition_to_proposed_yaml` is a pure formatting utility that belongs closer to `sdi.detection.boundaries` rather than buried in another CLI module.
- [2026-04-24 | "M11"] `cli/__init__.py:30`: `signal.signal(signal.SIGTERM, _sigterm_handler)` executes at module import time as a side effect. Acceptable for a pure-CLI entry point, but any test that does `import sdi.cli` will silently install the SIGTERM handler — worth noting if the test suite ever needs to control signal disposition.
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `assembly.py:158`, `snapshot_cmd.py:203`, and `_runner.py:152` each independently hardcode `repo_root / ".sdi" / "cache"`. Three sites for the same path with no shared constant. Centralizing as a helper or config attribute would reduce future update risk.
- [2026-04-24 | "Implement Milestone 10: Caching and Performance Optimization"] `DRIFT_LOG.md` pre-existing: the unresolved `diff_cmd.py:54-56` observation (noted by the coder as out of scope) should be moved to Resolved in the next housekeeping pass.
- [2026-04-24 | "architect audit"] `diff_cmd.py:54-56` `[2026-04-23 | "M08"]` — Observation only. The previous audit cycle recommended raising an error for partial spec; instead, the behavior was documented in the Click command help string ("With only SNAPSHOT_A, diffs A against the latest snapshot."). The observation explicitly labels itself "Observation only" and notes the help string is now accurate. No code change is warranted. Remove from DRIFT_LOG.md as resolved-by-documentation.

## Resolved
