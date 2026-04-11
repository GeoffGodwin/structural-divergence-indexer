# Reviewer Report — M06 Pattern Fingerprinting and Catalog

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `categories.py:67-70` — The `async_patterns` query includes `(function_definition) @async_def` which matches ALL function definitions, not just async ones. The correct tree-sitter query for Python async functions requires a field predicate (`"async"` keyword marker). As-written, the category will include every function definition, inflating entropy for non-async codebases. Not urgent since these queries are not executed in M06, but should be corrected before the parsing adapters run them.
- `catalog.py:21` — TYPE_CHECKING import of `CommunityResult` from `sdi.detection.leiden` creates a type-level dependency from patterns → detection, which CLAUDE.md prohibits ("sdi/patterns/ depends on sdi/parsing/ output — NOT on graph or detection"). At runtime this is a no-op (guarded by TYPE_CHECKING + `from __future__ import annotations`), but the conceptual boundary is still crossed. Consider defining a `PartitionProtocol` in patterns (or accepting the duck-typed dict) to keep the type boundary clean.
- `catalog.py:22` — TYPE_CHECKING import of `FeatureRecord` from `sdi.snapshot.model` instead of `sdi.parsing`. Per CLAUDE.md, patterns depends on parsing output, and `sdi.parsing.__init__` is the declared home of `FeatureRecord`. Using the snapshot module as the import source inverts the intended layer ordering (snapshot depends on patterns, not the other way around).
- `catalog.py:240-264` — `_compute_velocity` takes both `prev_catalog` and `prev_cat` as arguments. `prev_cat` is derived from `prev_catalog` by the caller, making the `prev_catalog` argument exist solely for a None-check. The function would be cleaner as `_compute_velocity(hash_val, current_count, prev_cat, *, has_prev: bool)` or by folding the None-guard into the call site.

## Coverage Gaps
- The 11 Python files in `tests/fixtures/high-entropy/` are never parsed by any test in M06. The "high-entropy" assertions in `test_catalog_velocity_spread.py` use fully synthetic in-memory records with hardcoded hash strings, not the fixture files. An integration test that actually parses these fixtures with tree-sitter and asserts `entropy >= 4` for `error_handling` would validate that the queries and the parsing adapters agree with the fixture design intent.
- No test exercises `compute_structural_hash` with a deeply nested descriptor to confirm that recursive `_normalize_serialize` produces a stable, expected hash string. Current tests confirm hash equality/inequality properties but not the actual serialized form.

## Drift Observations
- `tests/unit/test_catalog.py:24-49` and `tests/unit/test_catalog_velocity_spread.py:23-44` — `make_record()`, `make_instance()`, and `default_config()` helpers are duplicated verbatim across both test files. These could be promoted to `conftest.py` (where `sample_pattern_catalog` and `sample_community_result` already live) to remove the duplication.
- `sdi.snapshot.model.FeatureRecord` vs `sdi.parsing.FeatureRecord` — `conftest.py` imports from `sdi.parsing`, but `test_catalog.py` and `test_catalog_velocity_spread.py` import from `sdi.snapshot.model`. These should agree on a single canonical location per CLAUDE.md.
- `ShapeStats.to_dict()` deduplicates `file_paths` via `sorted(set(...))` on serialization but the in-memory `file_paths` list may contain duplicates (one entry per instance occurrence). This means `instance_count` and `len(file_paths)` mean different things (instances vs unique files), which is intentional but undocumented — a comment on `ShapeStats.file_paths` clarifying "one path per occurrence, may contain duplicates" would prevent future confusion.
