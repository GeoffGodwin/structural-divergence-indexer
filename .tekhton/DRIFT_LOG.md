# Drift Log

## Metadata
- Last audit: 2026-04-11
- Runs since audit: 4

## Unresolved Observations
- [2026-04-11 | "M08"] `snapshot_cmd.py:184`, `show_cmd.py:117`, `diff_cmd.py:121`, `trend_cmd.py:84`, `check_cmd.py:166`, `catalog_cmd.py:102` — All six new M08 CLI commands construct `snapshots_dir = repo_root / config.snapshots.dir` with no path bounds check. This is the same pattern the security agent flagged at `assembly.py:122` (LOW, fixable). M08 has introduced six new instances of the same pattern. The security fix for assembly.py should be applied uniformly to all call sites.
- [2026-04-11 | "M08"] `diff_cmd.py:22-66` — `_load_pair` only handles the case where both refs are None (default to last two) or both are non-None. If only one of `ref_a`/`ref_b` is provided by the user, the function falls through to the `else` branch and calls `resolve_snapshot_ref` on the non-None value while passing the None value through, which resolves to "latest" — silently treating a partial spec as a full two-ref diff. This implicit behavior is undocumented.
- [2026-04-11 | "M07"] `delta.py:102` — `_count_boundary_violations` uses `int(e.get("count", 1))` with a default of **1** (not 0). An edge dict present without a `count` key is silently treated as one crossing. Either assert `count` is always present or use 0 and document the rationale.
- [2026-04-11 | "M07"] `assembly.py:136-150` — `snap` is constructed with a throwaway `_null_divergence()` placeholder that is immediately overwritten on the next line. All data needed for `compute_delta` is available before `Snapshot` construction; restructuring to construct `Snapshot` once with the real divergence would be cleaner and eliminate the mutable placeholder pattern.
- [2026-04-11 | "M06"] `tests/unit/test_catalog.py:24-49` and `tests/unit/test_catalog_velocity_spread.py:23-44` — `make_record()`, `make_instance()`, and `default_config()` helpers are duplicated verbatim across both test files. These could be promoted to `conftest.py` (where `sample_pattern_catalog` and `sample_community_result` already live) to remove the duplication.
- [2026-04-11 | "M06"] `sdi.snapshot.model.FeatureRecord` vs `sdi.parsing.FeatureRecord` — `conftest.py` imports from `sdi.parsing`, but `test_catalog.py` and `test_catalog_velocity_spread.py` import from `sdi.snapshot.model`. These should agree on a single canonical location per CLAUDE.md.
- [2026-04-11 | "M06"] `ShapeStats.to_dict()` deduplicates `file_paths` via `sorted(set(...))` on serialization but the in-memory `file_paths` list may contain duplicates (one entry per instance occurrence). This means `instance_count` and `len(file_paths)` mean different things (instances vs unique files), which is intentional but undocumented — a comment on `ShapeStats.file_paths` clarifying "one path per occurrence, may contain duplicates" would prevent future confusion.
- [2026-04-11 | "M05"] `test_leiden.py:36-40` and `test_leiden_internals.py:36-40` still duplicate the `_make_graph` helper verbatim. Consolidation into `tests/conftest.py` or a shared `tests/unit/helpers.py` remains a pending cleanup.

## Resolved
