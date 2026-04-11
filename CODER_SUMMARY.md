# Coder Summary
## Status: COMPLETE (rework cycle 1)

## What Was Implemented

### Milestone 5: Leiden Community Detection and Partition Stability

Created the `src/sdi/detection/` package implementing Stage 3 of the pipeline.

**`CommunityResult` dataclass** (`leiden.py`):
- `partition`: cluster assignment per vertex (igraph vertex id → cluster id)
- `stability_score`: fraction of nodes retaining stable cluster membership (1.0 on cold start or unchanged graph)
- `cluster_count`: number of distinct clusters detected
- `inter_cluster_edges`: list of `{"source_cluster", "target_cluster", "count"}` dicts for directed edges crossing boundaries
- `surface_area_ratios`: per-cluster ratio of boundary-crossing edges to total edges touching that cluster
- `vertex_names`: ordered file paths corresponding to partition indices (Seeds Forward for M06/M07/M09)

**Leiden wrapper** (`leiden.py` + `_partition_cache.py`):
- `run_leiden(graph, config, cache_dir)`: main entry point
- Cold start: seeds from `config.core.random_seed` (default 42) → deterministic results
- Warm start: builds `initial_membership` from cached stable partition; seeds Leiden from same random seed for reproducibility
- Graph with `< 10` nodes: emits `warnings.warn("insufficient structure for boundary detection")` and returns trivial partition (all nodes in cluster 0)
- `leiden_gamma` from `config.boundaries.leiden_gamma` passed as `resolution_parameter`

**Partition cache** (`_partition_cache.py`):
- Schema: `{"cache_version": "0.1.0", "vertex_names": [...], "stable_partition": [...], "node_history": {...}}`
- Includes `cache_version` field for future compatibility (Seeds Forward requirement)
- Atomic write via `tempfile.mkstemp` + `os.replace()`
- Missing or corrupt cache → cold start without error

**Stability threshold debounce** (`_partition_cache.py/_apply_debounce`):
- Per-node tracking: `stable_cluster`, `candidate_cluster`, `consecutive_runs`
- Node only promoted to new cluster after `stability_threshold` consecutive runs in that cluster
- Flicker (node returns to stable cluster) resets counter to 0
- New nodes (not in prior cache) accepted immediately

**Tests** (`test_leiden.py` + `test_leiden_internals.py`):
- 30 tests total, all passing (11 detection-level, 19 internal unit tests)
- Coverage: cold start determinism, warm start stability (1.0 on unchanged graph), gamma effect on cluster count, trivial partition for small graphs, cache round-trip, corrupt cache fallback, debounce promotion and flicker reset, stability score computation, inter-cluster edge counting, surface area ratio computation

## Architecture Change Proposals

**New file: `_partition_cache.py`** — The 300-line ceiling required splitting `leiden.py`. Cache I/O, debounce, and stability score computation were extracted to `src/sdi/detection/_partition_cache.py`. The milestone only specified `leiden.py` and `__init__.py`, but the ceiling left no alternative. Both `leiden.py` and `tests/unit/test_leiden_internals.py` import directly from `_partition_cache` — the module boundary is clean (cache management is a distinct concern).

- **Current constraint**: Milestone spec named `leiden.py` and `__init__.py` as the only files
- **What triggered this**: `leiden.py` was 431 lines (300-line ceiling is hard)
- **Proposed change**: Extracted cache/debounce/stability functions to `_partition_cache.py`; `leiden.py` imports from it
- **Backward compatible**: Yes — `detect_communities` public API is unchanged
- **ARCHITECTURE.md update needed**: No — `_partition_cache.py` is a private helper within the `detection` package

## Files Modified

| File | Change |
|---|---|
| `src/sdi/detection/__init__.py` | **New.** Public API: `detect_communities(graph, config, cache_dir) -> CommunityResult`. |
| `src/sdi/detection/leiden.py` | **New.** `CommunityResult` dataclass, `_compute_inter_cluster_edges`, `_compute_surface_area_ratios`, `run_leiden`. |
| `src/sdi/detection/_partition_cache.py` | **New.** `PARTITION_CACHE_VERSION`, `_read_cache`, `_write_cache`, `_build_initial_membership`, `_apply_debounce`, `_compute_stability_score`. |
| `tests/unit/test_leiden.py` | **New.** 11 detection-level tests (cold start, warm start, gamma, trivial partition, cache, community result shape). |
| `tests/unit/test_leiden_internals.py` | **New.** 20 internal unit tests (debounce, cache I/O, stability score, metrics). |

### Rework cycle 1 changes

| File | Change |
|---|---|
| `src/sdi/detection/leiden.py` | **Fixed.** `_compute_surface_area_ratios`: removed `cluster_count` parameter; cluster IDs are now derived from `set(partition)` directly. Updated call site in `run_leiden` (dropped third argument). |
| `tests/unit/test_leiden_internals.py` | **Fixed.** Removed `cluster_count` keyword argument from all three `_compute_surface_area_ratios` call sites. Updated `test_surface_area_ratios_empty_cluster` to assert `set(ratios.keys()) == {0, 2}` (was masking the bug by passing `cluster_count=3` for a 2-element set). Added `test_surface_area_ratios_non_contiguous_ids` verifying that non-contiguous IDs like `[0, 0, 4, 4]` produce keys `{0, 4}` and not the incorrect range `{0, 1}`. |

## Human Notes Status
No human notes in this task.

## Observed Issues (out of scope)
None observed.
