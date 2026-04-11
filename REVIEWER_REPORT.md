# Reviewer Report — M05: Leiden Community Detection and Partition Stability
Review cycle: 2 of 4

## Verdict
APPROVED_WITH_NOTES

## ACP Verdicts
- ACP: `_partition_cache.py` extraction — ACCEPT: 300-line ceiling compliance with clean concern separation. Cache I/O + debounce is a distinct concern from algorithm coordination. Private module, no public API surface change.

## Prior Blocker Verification

**[FIXED] leiden.py `_compute_surface_area_ratios` non-contiguous cluster ID bug**

Evidence: `leiden.py:127` now does `cluster_ids = set(partition)` and the function signature no longer accepts a `cluster_count` parameter. The return dict on `leiden.py:142-145` iterates `cluster_ids` directly — no range-based assumption. The call site at `leiden.py:236` passes only `(graph, stable_partition)`. `test_leiden_internals.py:284-291` now asserts `set(ratios.keys()) == {0, 2}` for partition `[0, 0, 2]`. `test_leiden_internals.py:293-307` adds the `test_surface_area_ratios_non_contiguous_ids` test explicitly covering partition `[0, 0, 4, 4]` with expected keys `{0, 4}`. Blocker is fully resolved.

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `leiden.py:32-37,43-48`: module-level `ImportError` guard still uses `print(file=sys.stderr)` rather than `click.echo(..., err=True)`. Acceptable at import time (Click context unavailable); carry forward from cycle 1 for cleanup pass.
- `_partition_cache.py` `_read_cache`: exception tuple still does not include `AttributeError` or `TypeError`. A top-level JSON array parses without error but `.get()` raises `AttributeError`. Stated contract is "corrupt cache → cold start without error." Add `AttributeError, TypeError` or an `isinstance(data, dict)` guard. Carry forward from cycle 1.
- `_partition_cache.py` `_read_cache` return type: `dict | None` is still unparameterized — should be `dict[str, Any] | None` for mypy strictness. Minor.

## Coverage Gaps
- `_read_cache` still not tested with a top-level JSON array as file content (e.g., `[1,2,3]`); should return `None` without raising. Carry forward from cycle 1.
- `_build_initial_membership` still not tested with a cache that passes `_read_cache` validation but is missing `vertex_names` or `stable_partition` keys — KeyError would propagate to caller. Carry forward from cycle 1.
- Non-contiguous cluster ID coverage gap from cycle 1 is now resolved by `test_surface_area_ratios_non_contiguous_ids`.

## Drift Observations
- `test_leiden.py:36-40` and `test_leiden_internals.py:36-40` still duplicate the `_make_graph` helper verbatim. Consolidation into `tests/conftest.py` or a shared `tests/unit/helpers.py` remains a pending cleanup.
