# Coder Summary
## Status: COMPLETE

## What Was Implemented

**Stage 2 of the SDI pipeline: dependency graph construction and metrics.**

- **`src/sdi/graph/builder.py`** — `build_dependency_graph(records, config) -> tuple[igraph.Graph, dict]`
  - Builds directed igraph.Graph with one vertex per source file (vertex attribute `"name"` = file_path)
  - Resolves imports to intra-project files via exact match + longest-suffix match (handles package-prefixed imports like `pkg.models.user` → `models/user.py`)
  - External and stdlib imports are silently dropped (counted in `unresolved_count` metadata)
  - Self-imports are skipped (counted in `self_import_count` metadata)
  - Duplicate imports: single edge (unweighted) or summed weight (weighted)
  - `config.boundaries.weighted_edges = True` adds `weight` attribute to edges
  - Deterministic: vertices sorted alphabetically, records processed in sorted order

- **`src/sdi/graph/metrics.py`** — `compute_graph_metrics(graph) -> dict`
  - Returns all snapshot-schema keys: `node_count`, `edge_count`, `density`, `cycle_count`, `hub_concentration`, `hub_nodes`, `component_count`, `max_depth`
  - Cycle count: `graph.simple_cycles()` (exact count of simple directed cycles)
  - Hub concentration: ratio of nodes with in-degree ≥ 3 to total nodes; 0.0 for n < 3
  - Component count: weakly-connected components via `connected_components(mode="weak")`
  - Max depth: graph diameter via `graph.diameter(directed=True)`
  - All metrics return 0/0.0/[] for empty graph

- **`src/sdi/graph/__init__.py`** — public API re-export

- **`tests/unit/test_graph_builder.py`** (70 tests) — covers: module key derivation, module map construction, import resolution (exact/suffix/no-match/longest-suffix), empty input, node/edge counts, vertex names, determinism, external import exclusion, self-import handling, duplicate imports (weighted/unweighted), suffix-based resolution, cycle edge creation

- **`tests/unit/test_graph_metrics.py`** (70 tests) — covers: all-zero empty graph, single node, density variants, acyclic/cyclic cycle counts, disconnected components, max depth on DAG/chain, hub detection/concentration, return schema key presence and types

## Root Cause (bugs only)
N/A — feature implementation

## Files Modified
- `src/sdi/graph/__init__.py` (NEW)
- `src/sdi/graph/builder.py` (NEW)
- `src/sdi/graph/metrics.py` (NEW)
- `tests/unit/test_graph_builder.py` (NEW)
- `tests/unit/test_graph_metrics.py` (NEW)

## Human Notes Status
N/A — no human notes listed

## Architecture Change Proposals

No architecture changes required. The implementation follows the module boundaries defined in CLAUDE.md: `sdi/graph/` depends on `sdi/parsing/` output (FeatureRecords) and igraph, with no imports from `sdi/cli/`. The `build_dependency_graph` return type matches the Seeds Forward annotation: `igraph.Graph` is directly passable to `detection/leiden.py` in M05, and the metrics dict key names (`node_count`, `edge_count`, `density`, `cycle_count`, `hub_concentration`, `component_count`, `max_depth`) are locked as snapshot schema fields for M07.

The PM annotation on `hub_concentration` was implemented as: threshold = `HUB_INDEGREE_THRESHOLD` (3), hub_nodes = nodes with in-degree ≥ 3, hub_concentration = count/n. The "top 10%" language in the PM note is treated as explanatory context, not a second algorithm. The constant `HUB_INDEGREE_THRESHOLD = 3` is exported for downstream consumers.
