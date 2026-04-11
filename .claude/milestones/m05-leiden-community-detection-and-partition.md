### Milestone 5: Leiden Community Detection and Partition Stability
<!-- milestone-meta
id: "05"
status: "done"
-->


**Scope:** Build Stage 3 of the pipeline — run the Leiden community detection algorithm on the dependency graph to identify structural boundaries. Implement partition seeding (from cache on warm starts, from fixed random seed on cold starts), partition stability scoring, and the stability threshold debounce. Write partition cache to `.sdi/cache/partition.json`.

**Deliverables:**
- `src/sdi/detection/__init__.py` with `detect_communities(graph: igraph.Graph, config: SDIConfig, cache_dir: Path) -> CommunityResult` public API
- `src/sdi/detection/leiden.py` with Leiden algorithm wrapper: gamma parameter from config, seeding from previous partition, cold-start seeding from `config.random_seed`, stability scoring (percentage of nodes retaining cluster membership), stability threshold debounce, partition cache read/write
- `CommunityResult` dataclass: `partition` (cluster assignments), `stability_score` (float 0–1), `cluster_count`, `inter_cluster_edges` (dependency directionality between clusters), `surface_area_ratios` (interface surface per cluster)
- `tests/unit/test_leiden.py`

**Acceptance criteria:**
- Cold-start Leiden with `random_seed = 42` produces identical results across runs on the same graph
- Warm-start Leiden seeded from a previous partition produces stable results (stability score > 0.9 when graph has not changed)
- Partition is written to `.sdi/cache/partition.json` after every run using atomic writes
- Stability score is computed as the fraction of nodes that retained their cluster membership from the previous partition
- Stability threshold debounce: a node must appear in a new cluster for `stability_threshold` consecutive runs (default: 3) before the partition reflects the change
- `leiden_gamma` from config is passed to `leidenalg.find_partition()` as the resolution parameter
- Graph with fewer than 10 nodes produces a warning ("insufficient structure for boundary detection") and returns a trivial partition (all nodes in one cluster)
- Partition cache is read on startup; missing cache triggers cold start without error
- `pytest tests/unit/test_leiden.py` passes

**Tests:**
- `tests/unit/test_leiden.py`: Cold start determinism (same graph + same seed = same partition across runs), warm start stability (unchanged graph has stability score 1.0), warm start with small change has high stability score, gamma parameter affects cluster count (higher gamma = more clusters), stability threshold debounce (node flickers back and forth, doesn't settle until N consecutive runs), graph with < 10 nodes returns warning and trivial partition, partition cache round-trip (write then read produces same partition), missing cache file triggers cold start gracefully

**Watch For:**
- leidenalg's `find_partition` API: use `leidenalg.find_partition(graph, leidenalg.RBConfigurationVertexPartition, resolution_parameter=gamma, seed=seed)` — the seed parameter controls reproducibility
- Partition seeding for warm starts: use the `initial_membership` parameter, mapping from previous partition's cluster assignments to the current graph's nodes (nodes added since last run get no initial assignment)
- The stability threshold debounce requires tracking consecutive run counts per node — store this in the partition cache alongside the partition itself
- igraph and leidenalg must agree on vertex ordering — use the same graph object, never rebuild

**Seeds Forward:**
- `CommunityResult.partition` is used by `detection/boundaries.py` in Milestone 9 to compute intent divergence against the ratified boundary spec
- `CommunityResult.inter_cluster_edges` feeds into the boundary violation velocity computation in Milestone 7
- The partition cache at `.sdi/cache/partition.json` must be readable by future milestones — its schema should include a version field
- Cluster assignments map files to boundary groups — this mapping is used by pattern boundary-spread computation in Milestone 6

---
