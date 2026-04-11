# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in REVIEWER_REPORT.md.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-11 | "M07"] `assembly.py:158` — `_null_divergence()` still declares return type `Any` and still performs a late import of `DivergenceSummary`. The late import avoids a circular dependency concern that does not actually exist here (`DivergenceSummary` is in the same package). Import at module top and tighten the return type to `DivergenceSummary`.
- [ ] [2026-04-11 | "M07"] `delta.py:39,57` — `PatternCatalog.from_dict(catalog_dict)` is called twice per snapshot (once in `_catalog_pattern_entropy`, once in `_catalog_convention_drift`). For large catalogs this doubles deserialization cost; a single `_load_catalog` helper passed to both callers would eliminate the redundancy.
- [ ] [2026-04-11 | "M07"] `assembly.py:128-139` — `records: list[FeatureRecord]` are not stored in the assembled Snapshot (field defaults to `[]`). If future commands need per-file data the snapshot will not be able to supply it.
- [ ] [2026-04-11 | "M06"] `categories.py:67-70` — The `async_patterns` query includes `(function_definition) @async_def` which matches ALL function definitions, not just async ones. The correct tree-sitter query for Python async functions requires a field predicate (`"async"` keyword marker). As-written, the category will include every function definition, inflating entropy for non-async codebases. Not urgent since these queries are not executed in M06, but should be corrected before the parsing adapters run them.
- [ ] [2026-04-11 | "M06"] `catalog.py:21` — TYPE_CHECKING import of `CommunityResult` from `sdi.detection.leiden` creates a type-level dependency from patterns → detection, which CLAUDE.md prohibits ("sdi/patterns/ depends on sdi/parsing/ output — NOT on graph or detection"). At runtime this is a no-op (guarded by TYPE_CHECKING + `from __future__ import annotations`), but the conceptual boundary is still crossed. Consider defining a `PartitionProtocol` in patterns (or accepting the duck-typed dict) to keep the type boundary clean.
- [ ] [2026-04-11 | "M06"] `catalog.py:22` — TYPE_CHECKING import of `FeatureRecord` from `sdi.snapshot.model` instead of `sdi.parsing`. Per CLAUDE.md, patterns depends on parsing output, and `sdi.parsing.__init__` is the declared home of `FeatureRecord`. Using the snapshot module as the import source inverts the intended layer ordering (snapshot depends on patterns, not the other way around).
- [ ] [2026-04-11 | "M06"] `catalog.py:240-264` — `_compute_velocity` takes both `prev_catalog` and `prev_cat` as arguments. `prev_cat` is derived from `prev_catalog` by the caller, making the `prev_catalog` argument exist solely for a None-check. The function would be cleaner as `_compute_velocity(hash_val, current_count, prev_cat, *, has_prev: bool)` or by folding the None-guard into the call site.
- [ ] [2026-04-11 | "M05"] `leiden.py:32-37,43-48`: module-level `ImportError` guard still uses `print(file=sys.stderr)` rather than `click.echo(..., err=True)`. Acceptable at import time (Click context unavailable); carry forward from cycle 1 for cleanup pass.
- [ ] [2026-04-11 | "M05"] `_partition_cache.py` `_read_cache`: exception tuple still does not include `AttributeError` or `TypeError`. A top-level JSON array parses without error but `.get()` raises `AttributeError`. Stated contract is "corrupt cache → cold start without error." Add `AttributeError, TypeError` or an `isinstance(data, dict)` guard. Carry forward from cycle 1.
- [ ] [2026-04-11 | "M05"] `_partition_cache.py` `_read_cache` return type: `dict | None` is still unparameterized — should be `dict[str, Any] | None` for mypy strictness. Minor.

(All items resolved — see Resolved section below.)
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
