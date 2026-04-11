# Coder Summary
## Status: COMPLETE

## What Was Implemented

- **`src/sdi/snapshot/model.py`**: Added three new optional fields to `Snapshot` — `graph_metrics`, `pattern_catalog`, and `partition_data` — so that `compute_delta()` can compare two snapshots without re-running the pipeline. All fields default to `{}` and are fully round-tripped through `to_dict()` / `from_dict()`.

- **`src/sdi/snapshot/delta.py`** (NEW): `compute_delta(current, previous)` computing all four SDI dimensions:
  - `pattern_entropy` / `pattern_entropy_delta`: sum of distinct shapes across all categories
  - `convention_drift` / `convention_drift_delta`: fraction non-canonical / net new-minus-lost shapes
  - `coupling_topology` / `coupling_topology_delta`: normalized composite of density, hub_concentration, cycle_count/n, max_depth/n
  - `boundary_violations` / `boundary_violations_delta`: sum of inter-cluster edge counts
  - Returns null deltas when `previous` is None (first snapshot) or when major versions differ (emits UserWarning)

- **`src/sdi/snapshot/trend.py`** (NEW): `TrendData` dataclass and `compute_trend(snapshots, dimensions)`. Extracts per-dimension time series from ordered snapshot list; handles None values for first-snapshot deltas; dimension filter silently omits unknown names.

- **`src/sdi/snapshot/assembly.py`** (NEW): `assemble_snapshot(records, graph_metrics, community, catalog, config, commit_sha, timestamp, repo_root)`. Loads previous snapshot from disk, calls `compute_delta()`, writes snapshot atomically, enforces retention. Also includes `_compute_config_hash()` that hashes analysis-affecting config only.

- **`src/sdi/snapshot/__init__.py`**: Exported `assemble_snapshot`, `compute_delta`, `compute_trend`, `TrendData`, `ALL_DIMENSIONS`.

- **`tests/unit/test_delta.py`** (NEW): 19 tests covering all seven acceptance criteria: first snapshot nulls, identical snapshots zeros, pattern entropy from known catalogs, convention drift rate (new minus lost), coupling topology from known metrics, boundary violation velocity, incompatible version warning.

- **`tests/unit/test_trend.py`** (NEW): 14 tests covering five-snapshot time series, dimension filter, single-snapshot baseline, null delta handling, serialization.

## Root Cause (bugs only)
N/A — feature implementation

## Files Modified
- `src/sdi/snapshot/model.py` (modified) — added graph_metrics, pattern_catalog, partition_data fields to Snapshot
- `src/sdi/snapshot/delta.py` (NEW) — compute_delta() with four SDI dimension computations
- `src/sdi/snapshot/trend.py` (NEW) — TrendData dataclass and compute_trend()
- `src/sdi/snapshot/assembly.py` (NEW) — assemble_snapshot() with write+retention enforcement
- `src/sdi/snapshot/__init__.py` (modified) — export new public APIs
- `tests/unit/test_delta.py` (NEW) — delta computation unit tests (284 lines)
- `tests/unit/test_trend.py` (NEW) — trend computation unit tests (226 lines)

## Human Notes Status
No human notes provided.

## Architecture Change Proposals

### assemble_snapshot() signature differs from milestone spec

**Current constraint**: Milestone specifies `assemble_snapshot(records, graph, metrics, community, catalog, config, commit_sha, timestamp)` — includes `graph` (igraph.Graph object) and no `repo_root`.

**What triggered this**: The raw `graph` object is not needed for v1 assembly — all required data is already in `metrics` (pre-computed by `compute_graph_metrics()`) and `community` (which contains `inter_cluster_edges`). Including igraph.Graph would couple assembly to igraph unnecessarily. `repo_root: Path` is required to resolve `config.snapshots.dir` (which is a relative path string in the config).

**Proposed change**:
- Removed `graph` parameter
- Added `repo_root: Path` parameter
- Signature: `assemble_snapshot(records, graph_metrics, community, catalog, config, commit_sha, timestamp, repo_root)`

**Backward compatible**: N/A — new function, no existing callers.

**ARCHITECTURE.md update needed**: No — architecture doc describes modules abstractly.

## Metric Definitions (documented for reviewer)

| Metric | Absolute value | Delta computation |
|--------|---------------|------------------|
| `pattern_entropy` | Sum of distinct shape counts across all categories | current - previous |
| `convention_drift` | Fraction of non-canonical pattern instances (0.0–1.0) | len(new_shapes) - len(lost_shapes) |
| `coupling_topology` | avg(density, hub_concentration, cycle_count/n, max_depth/n) | current - previous |
| `boundary_violations` | Sum of all inter_cluster_edge counts | current - previous |

`convention_drift_delta` uses explicit set difference (`new_shapes - lost_shapes`) rather than simple subtraction, capturing the "net new shapes appearing minus shapes being consolidated" semantic described in the milestone "Watch For" section.

## Observed Issues (out of scope)
- `src/sdi/detection/_partition_cache.py:45`: `_read_cache()` does `data.get("cache_version")` without checking that `data` is a dict first. If the cache file contains a JSON array (not an object), this raises `AttributeError`. The test `test_leiden_internals.py::test_read_cache_toplevel_array_returns_none` documents this as a pre-existing failure.
