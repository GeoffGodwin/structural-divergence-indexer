### Milestone 4: Community Detection and Boundary Management

**Scope:** Implement Stage 3 of the pipeline: Leiden community detection on the dependency graph, partition stability scoring, boundary specification parsing and management, and the `sdi boundaries` command. This milestone delivers the boundary inference and ratification workflow.

**Deliverables:**
- Leiden algorithm wrapper: runs community detection, supports seeding from previous partition, uses fixed random seed on cold start
- Partition stability scoring: percentage of nodes that kept cluster membership versus previous run
- Stability threshold enforcement: only update boundary map if a node moved in N consecutive runs (debounce)
- Boundary specification parser: reads and validates `.sdi/boundaries.yaml`
- Intent divergence computation: compares detected communities against ratified boundary spec
- Partition cache: reads/writes `.sdi/cache/partition.json`
- `sdi boundaries` command: `--propose` (show inferred boundaries), `--ratify` (open in `$EDITOR`), `--export`, `--format`
- `sdi init` updated to run initial inference and optionally write a starter boundary spec

**Files to create or modify:**
- `src/sdi/detection/__init__.py`
- `src/sdi/detection/leiden.py`
- `src/sdi/detection/boundaries.py`
- `src/sdi/cli/boundaries_cmd.py`
- `src/sdi/cli/init_cmd.py` (update)
- `tests/unit/test_leiden.py`
- `tests/unit/test_boundaries.py`

**Acceptance criteria:**
- Leiden detection produces cluster assignments for every node in the graph
- Cold start uses `random_seed` from config (default: 42) and produces deterministic results
- Warm start seeds from `.sdi/cache/partition.json` and produces stable partitions (>90% node stability for unchanged graphs)
- `stability_threshold` debounce works: a node only changes cluster assignment after N consecutive runs in the new cluster
- `.sdi/boundaries.yaml` is parsed and validated: required fields checked, `version` field present
- Missing `.sdi/boundaries.yaml` is not an error — intent divergence is simply not computed
- Malformed `.sdi/boundaries.yaml` exits with code 2 and descriptive error with line reference
- `sdi boundaries` shows current ratified boundary map in text format
- `sdi boundaries --propose` runs inference and shows proposed changes without modifying the ratified spec
- `sdi boundaries --ratify` opens `$EDITOR` (falls back to `vi`) with the proposed boundaries
- `sdi boundaries --export path.yaml` writes boundary spec to the specified path
- Intent divergence computes: modules in detected-but-not-ratified, modules in ratified-but-not-detected, mismatched file assignments
- Graph with fewer than 10 nodes produces a warning ("insufficient structure for boundary detection") and skips boundary metrics

**Tests:**
- `tests/unit/test_leiden.py`:
  - Deterministic output on same graph with same seed
  - Seeded partition is stable for unchanged graph
  - Partition stability score computation is correct
  - Stability threshold debounce: node flapping between clusters is suppressed
  - Small graph (<10 nodes) reports warning, does not error
- `tests/unit/test_boundaries.py`:
  - Valid YAML parses correctly with all fields extracted
  - Missing optional fields (`layers`, `allowed_cross_domain`, `aspirational_splits`) do not error
  - Invalid YAML produces exit code 2
  - Missing `version` field produces validation error
  - Intent divergence correctly identifies added, removed, and mismatched modules

**Watch For:**
- `leidenalg` requires `igraph` to be installed first. Ensure the dependency order is correct in `pyproject.toml`.
- The Leiden algorithm's `leidenalg.find_partition()` takes a `seed` parameter for reproducibility. Ensure this is set from config on cold start.
- Partition cache must handle the case where the graph topology changed (nodes added/removed) since the cached partition. Map by vertex name (file path), not by vertex index.
- `$EDITOR` may not be set. Provide a fallback chain: `$EDITOR` → `$VISUAL` → `vi`.
- The `--ratify` flag involves spawning an external editor, which is platform-dependent. Test on both Linux and macOS.

**Seeds Forward:**
- Cluster assignments from Leiden are inputs to pattern boundary spread computation in Milestone 5.
- The `BoundarySpec` data structure from `boundaries.py` is used in snapshot assembly (Milestone 6) for intent divergence inclusion.
- The partition cache pattern (write JSON to `.sdi/cache/`, read on next run) is reused by the fingerprint cache.
- Inter-cluster dependency graph and surface area ratio are included in the snapshot (Milestone 6).

---
