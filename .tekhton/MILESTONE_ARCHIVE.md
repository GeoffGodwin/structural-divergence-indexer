# Milestone Archive

Completed milestone definitions archived from CLAUDE.md.
See git history for the commit that completed each milestone.

---

## Archived: 2026-04-23 — Unknown Initiative

### Milestone 1: Project Skeleton, Config System, and Core Data Structures
<!-- milestone-meta
id: "01"
status: "done"
-->


**Scope:** Establish the project foundation — `pyproject.toml`, package structure, the `sdi` CLI entry point with Click, the complete configuration loading system with five-level precedence, and the core data structures (`FeatureRecord`, `Snapshot`, `DivergenceSummary`) as dataclasses. No analysis logic — this milestone produces a CLI that can load config, print its version, and validate configuration. The `sdi init` command creates the `.sdi/` directory with a default config file.

**Deliverables:**
- `pyproject.toml` with PEP 621 metadata, all dependency declarations, entry point `sdi = "sdi.cli:cli"`, and extras (`[dev]`, `[all]`, `[web]`, `[systems]`)
- `src/sdi/__init__.py` with `__version__`
- `src/sdi/config.py` with full config loading (five-level precedence), validation (including threshold override expiry enforcement), and built-in defaults
- `src/sdi/cli/__init__.py` with root Click group, global flags (`--format`, `--no-color`, `--quiet`, `--verbose`), and top-level exception handler
- `src/sdi/cli/init_cmd.py` with `sdi init` that creates `.sdi/`, writes `config.toml` with commented defaults, and adds `.sdi/cache/` to `.gitignore`
- `src/sdi/snapshot/model.py` with `Snapshot`, `DivergenceSummary`, `FeatureRecord` dataclasses and JSON serialization/deserialization
- `src/sdi/snapshot/storage.py` with atomic file write utility (`write_atomic`) and snapshot read/write/list/retention-enforcement functions
- `tests/conftest.py` with shared fixtures (temporary directories, sample config dicts)
- `tests/unit/test_config.py`
- `tests/unit/test_snapshot_model.py`
- `tests/unit/test_storage.py`
- `.gitignore` with Python defaults + `.sdi/cache/`

**Acceptance criteria:**
- `pip install -e ".[dev]"` succeeds and `sdi --version` prints the version
- `sdi --help` lists all subcommand names (placeholders for unimplemented commands print "not yet implemented" and exit 1)
- `sdi init` creates `.sdi/config.toml` with all default values as comments, creates `.sdi/snapshots/` directory, and adds `.sdi/cache/` to `.gitignore`
- `sdi init --force` overwrites existing `.sdi/config.toml`
- `sdi init` in a non-git directory exits with code 2 and a descriptive error
- Config loading resolves CLI flags > env vars > project config > global config > defaults
- A config with `[thresholds.overrides.X]` missing `expires` exits with code 2
- Malformed TOML exits with code 2 with file path and line number
- `Snapshot` dataclass round-trips through JSON (serialize → deserialize → compare)
- `write_atomic` uses tempfile + `os.replace` — verified by test that simulates crash mid-write
- Snapshot retention enforcement deletes oldest files when count exceeds limit
- All unit tests pass: `pytest tests/unit/test_config.py tests/unit/test_snapshot_model.py tests/unit/test_storage.py`

**Tests:**
- `tests/unit/test_config.py`: Config loading from each precedence level, fallback to defaults, env var override, invalid TOML handling (check exit code 2 and error message), threshold override without `expires` rejected, expired override silently ignored, unknown keys produce deprecation warning
- `tests/unit/test_snapshot_model.py`: `Snapshot` JSON round-trip, `DivergenceSummary` with null deltas (first snapshot case), `snapshot_version` field presence, `FeatureRecord` construction
- `tests/unit/test_storage.py`: Atomic write creates file, atomic write does not produce partial file on simulated failure, snapshot listing sorted by timestamp, retention enforcement deletes oldest when limit exceeded, retention of 0 means unlimited

**Watch For:**
- Python 3.10 lacks `tomllib` in stdlib — must use `tomli` with a conditional import: `try: import tomllib except ImportError: import tomli as tomllib`
- `os.replace()` is atomic on POSIX but may not be on Windows across filesystems — tempfile must be created in the same directory as the target
- Click's `--no-color` flag and the `NO_COLOR` env var need to be wired into Rich's console configuration early — retrofitting is painful
- The top-level exception handler in `cli/__init__.py` must catch `SystemExit` to preserve exit codes while catching everything else as code 1

**Seeds Forward:**
- `config.py` is imported by every subsequent module — its API (`load_config() -> SDIConfig` dataclass) must be stable
- `FeatureRecord` dataclass defined here is the contract between Stage 1 (parsing) and Stages 2–4 — fields must include: `file_path`, `language`, `imports` (list of resolved import targets), `symbols` (list of defined names), `pattern_instances` (list of AST subtree descriptors), `lines_of_code`
- `Snapshot` dataclass must include fields for all four SDI dimensions plus `snapshot_version`, `timestamp`, `commit_sha`, `config_hash` — even though most are populated in later milestones
- `write_atomic()` in `storage.py` will be reused by boundary spec writes and cache writes
- The `sdi init` command will be extended in Milestone 9 to optionally write a starter `boundaries.yaml`

---

---

## Archived: 2026-04-23 — Unknown Initiative

### Milestone 2: File Discovery and Tree-Sitter Parsing
<!-- milestone-meta
id: "02"
status: "done"
-->


**Scope:** Build Stage 1 of the pipeline — file discovery with `.gitignore` filtering and configured exclude patterns, language detection by file extension, the base language adapter interface, and the Python language adapter as the first concrete implementation. This milestone produces `FeatureRecord` objects from Python source files via tree-sitter. Other language adapters (TypeScript, JavaScript, Go, Java, Rust) are deferred to Milestone 3.

**Deliverables:**
- `src/sdi/parsing/__init__.py` with `parse_repository(root: Path, config: SDIConfig) -> list[FeatureRecord]` public API
- `src/sdi/parsing/discovery.py` with file tree walking, `.gitignore` integration (via `pathspec` library or manual glob matching), configured exclude pattern filtering, and language detection by extension
- `src/sdi/parsing/base.py` with `LanguageAdapter` abstract base class defining the interface: `parse_file(path, source_bytes) -> FeatureRecord`, `language_name`, `file_extensions`, `grammar` property
- `src/sdi/parsing/python.py` with Python tree-sitter adapter: import extraction (regular imports, from-imports, relative imports), function/class definition extraction, symbol export detection, pattern instance extraction (try/except blocks, logging calls, data access patterns)
- Parallelized parsing via `ProcessPoolExecutor` with `SDI_WORKERS` config
- `tests/fixtures/simple-python/` fixture with 5–10 Python files with known import relationships, one try/except pattern variant, one cross-module dependency
- `tests/unit/test_discovery.py`
- `tests/unit/test_python_adapter.py` (tests for the Python adapter specifically)

**Acceptance criteria:**
- `parse_repository()` on `tests/fixtures/simple-python/` returns `FeatureRecord` objects for all `.py` files
- Each `FeatureRecord` has correct `imports`, `symbols`, `language`, and `pattern_instances` fields
- Files matching `.gitignore` patterns are excluded
- Files matching configured `exclude` patterns are excluded
- Language detection maps `.py` → Python, `.js` → JavaScript, `.ts` → TypeScript, etc.
- Files with no grammar available are skipped with a warning on stderr (not an error)
- If ALL files lack grammars, exit with code 3
- `SDI_WORKERS=1` runs parsing sequentially (for debugging)
- Tree-sitter CSTs are discarded after feature extraction — no CST objects retained in the returned list
- Python imports resolve relative imports to absolute paths relative to the repository root
- `pytest tests/unit/test_discovery.py tests/unit/test_python_adapter.py` passes

**Tests:**
- `tests/unit/test_discovery.py`: File discovery finds `.py` files, respects `.gitignore`, respects exclude patterns, detects languages by extension, empty directory returns empty list, hidden files (`.foo.py`) are included unless gitignored
- `tests/unit/test_python_adapter.py`: Parses simple function definitions, extracts `import X` and `from X import Y`, resolves relative imports (`from . import foo`), extracts class definitions, captures try/except as pattern instances, handles syntax errors gracefully (file skipped with warning), handles empty files

**Watch For:**
- tree-sitter 0.24+ changed the API for loading languages — use `tree_sitter.Language` from the grammar package, not the legacy `build_library` approach
- `.gitignore` parsing is surprisingly complex (negation patterns, directory-only patterns, nested `.gitignore` files) — consider using the `pathspec` library rather than hand-rolling
- Relative import resolution in Python (`from . import foo`) requires knowing the package structure — use the file path relative to the repository root to infer the package
- `ProcessPoolExecutor` requires that `FeatureRecord` is picklable — dataclasses with basic types are fine, but tree-sitter objects are NOT picklable (another reason to discard CSTs)

**Seeds Forward:**
- `FeatureRecord.imports` field format (list of absolute module paths as strings) is consumed by `graph/builder.py` in Milestone 4
- `FeatureRecord.pattern_instances` field format (list of dicts with `category`, `ast_hash`, `location`) is consumed by `patterns/fingerprint.py` in Milestone 6
- The `LanguageAdapter` base class interface must be stable — Milestone 3 adds five more adapters implementing it
- The `parse_repository()` function signature and return type are called from `snapshot_cmd.py` in Milestone 8
- The `simple-python` fixture is reused by integration tests in Milestones 8, 10, and 11

---

---

## Archived: 2026-04-23 — Unknown Initiative

### Milestone 3: Additional Language Adapters
<!-- milestone-meta
id: "03"
status: "done"
-->


**Scope:** Implement tree-sitter language adapters for TypeScript, JavaScript, Go, Java, and Rust. Each adapter implements the `LanguageAdapter` interface from Milestone 2 with language-specific import extraction, symbol detection, and pattern instance identification. Also build the `multi-language` test fixture.

**Deliverables:**
- `src/sdi/parsing/typescript.py` — TypeScript adapter (ES imports, CommonJS require, type imports, re-exports)
- `src/sdi/parsing/javascript.py` — JavaScript adapter (ES imports, CommonJS require, dynamic imports)
- `src/sdi/parsing/go.py` — Go adapter (import declarations, exported names via capitalization)
- `src/sdi/parsing/java.py` — Java adapter (import statements, package declarations, class definitions)
- `src/sdi/parsing/rust.py` — Rust adapter (use statements, mod declarations, pub items)
- `tests/fixtures/multi-language/` with 3–5 files per language (Python + TypeScript minimum), each with known imports and at least one pattern instance
- Unit tests for each adapter

**Acceptance criteria:**
- Each adapter correctly extracts imports, symbols, and pattern instances for its language
- `parse_repository()` on the `multi-language` fixture returns `FeatureRecord` objects for all supported languages present
- Missing grammar packages produce a warning, not an error — the adapter is simply not registered
- Each adapter handles syntax errors in source files gracefully (skip with warning)
- All existing tests continue to pass
- TypeScript adapter distinguishes type-only imports from value imports (both create edges, but type-only imports are annotated)

**Tests:**
- `tests/unit/test_typescript_adapter.py`: ES import extraction (`import { X } from 'Y'`), default imports, re-exports, type-only imports, CommonJS require
- `tests/unit/test_javascript_adapter.py`: ES import extraction, CommonJS require, dynamic import expressions
- `tests/unit/test_go_adapter.py`: Import declarations (single and grouped), exported symbol detection (capitalized names), function and struct definitions
- `tests/unit/test_java_adapter.py`: Import statements, wildcard imports, package declarations, class and interface definitions
- `tests/unit/test_rust_adapter.py`: Use statements (including nested paths), mod declarations, pub items, trait and impl blocks

**Watch For:**
- TypeScript and JavaScript share the same tree-sitter node types for imports — consider whether the JS adapter can be a thin subclass of the TS adapter, or if they should be independent
- Go import path resolution differs from other languages (package paths, not file paths) — the graph builder (Milestone 4) needs to handle this
- Java wildcard imports (`import java.util.*`) cannot be resolved to specific symbols without classpaths — record as a single edge to the package
- Rust's `mod` declarations create implicit file dependencies that don't look like imports — the adapter must detect `mod foo;` and resolve to `foo.rs` or `foo/mod.rs`
- Grammar packages may not be installed — each adapter should gracefully handle `ImportError` for its grammar and register itself only when the grammar is available

**Seeds Forward:**
- The import format differences between languages (file-path-based vs. package-based) must be normalized before reaching the graph builder — establish a convention in `FeatureRecord.imports` for how non-file-based imports (Go packages, Java packages) are represented
- Pattern instance extraction queries per language feed into the pattern fingerprinting in Milestone 6 — ensure each adapter produces `pattern_instances` in the same format
- The `multi-language` fixture is reused by graph construction tests in Milestone 4

---

---

## Archived: 2026-04-23 — Unknown Initiative


### Milestone 4: Dependency Graph Construction and Metrics
<!-- milestone-meta
id: "04"
status: "done"
-->
<!-- PM-tweaked: 2026-04-11 -->


**Scope:** Build Stage 2 of the pipeline — construct a directed dependency graph from `FeatureRecord` objects using igraph. Compute graph metrics: node count, edge count, density, connected components, cycle count, and hub concentration. Support both weighted (by import symbol count) and unweighted edges via config toggle.

**Deliverables:**
- `src/sdi/graph/__init__.py` with `build_dependency_graph(records: list[FeatureRecord], config: SDIConfig) -> tuple[igraph.Graph, dict]` public API
- `src/sdi/graph/builder.py` with graph construction: nodes from files/modules, directed edges from imports, optional edge weights from symbol counts
- `src/sdi/graph/metrics.py` with metric computation: `compute_graph_metrics(graph: igraph.Graph) -> dict` returning node count, edge count, density, connected component count, cycle count, hub nodes (high in-degree), max dependency depth
- `tests/unit/test_graph_builder.py`
- `tests/unit/test_graph_metrics.py`

**Acceptance criteria:**
- Given `FeatureRecord` objects from the `simple-python` fixture, the graph has the expected number of nodes and edges
- Each import in a `FeatureRecord` produces a directed edge from the importing file to the imported file
- Unresolved imports (external packages, stdlib) are excluded from the graph — only intra-project imports create edges
- `weighted_edges = true` in config produces edges with `weight` attribute equal to the number of symbols imported
- `weighted_edges = false` (default) produces unweighted edges
- Cycle detection correctly identifies circular imports
- Hub concentration identifies the top N nodes by in-degree
- Connected component count correctly handles disconnected subgraphs
- Graph is deterministic — same input produces same graph with same node/edge ordering
- `pytest tests/unit/test_graph_builder.py tests/unit/test_graph_metrics.py` passes

**Tests:**
- `tests/unit/test_graph_builder.py`: Graph from known imports has correct nodes/edges, external imports excluded, self-imports handled, weighted edges have correct weights, empty record list produces empty graph, duplicate imports create single edge (or weighted edge), unresolved relative imports logged as warning
- `tests/unit/test_graph_metrics.py`: Density calculation on known graphs, cycle count on acyclic graph (0) and cyclic graph (>0), hub detection identifies highest in-degree nodes, connected components count, max depth on DAG, metrics on empty graph return zeroes

**Watch For:**
- igraph node IDs are integers — maintain a mapping from file paths to node IDs and back, stored as vertex attributes (`graph.vs["name"] = file_path`)
- Import resolution must handle the case where the target file does not exist in the analyzed set (external dependency) — these edges are silently dropped, not errored
- Go and Java use package-based imports not file-based — the builder needs a resolution step that maps package names to file nodes, possibly via a mapping built during discovery
- Graph density for large sparse graphs can be very small (0.001) — ensure the metric is reported with sufficient decimal precision
- [PM: The `dict` in `build_dependency_graph`'s return type should contain import-resolution metadata: `{"unresolved_count": int, "self_import_count": int}`. The file-path-to-node-ID mapping is stored as vertex attributes on the graph itself (`graph.vs["name"]`), not in this dict. Returning it separately would duplicate data already in the graph.]
- [PM: `hub_concentration` in the metrics dict is a **scalar float**: the ratio of nodes whose in-degree exceeds a fixed threshold (in-degree ≥ 3, or equivalently the top 10% by in-degree, whichever is smaller) to total node count. Report it as `0.0` for graphs with fewer than 3 nodes. A separate `hub_nodes` key (list of file paths for nodes meeting the hub threshold) may be included in the metrics dict alongside the scalar for downstream use, but `hub_concentration` itself must be a float in [0.0, 1.0]. N for "top N" in the acceptance criteria refers to this threshold-based selection, not a fixed count.]

**Seeds Forward:**
- The `igraph.Graph` object is passed directly to `detection/leiden.py` in Milestone 5 — vertex names and edge structure must be stable
- The metrics dict is included in the snapshot JSON — its key names (`node_count`, `edge_count`, `density`, `cycle_count`, `hub_concentration`, `component_count`, `max_depth`) become part of the snapshot schema
- Cycle count delta and hub concentration delta are components of the "coupling topology delta" SDI dimension — Milestone 7 computes these deltas

---

## Archived: 2026-04-23 — Unknown Initiative

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

---

## Archived: 2026-04-23 — Unknown Initiative


### Milestone 6: Pattern Fingerprinting and Catalog
<!-- milestone-meta
id: "06"
status: "done"
-->
<!-- PM-tweaked: 2026-04-11 -->


**Scope:** Build Stage 4 of the pipeline — pattern fingerprinting, catalog construction, and entropy computation. Implement the seven built-in pattern categories, structural hashing of AST subtrees, canonical pattern identification, and per-shape velocity / boundary spread computation. This milestone produces the `PatternCatalog` with entropy measurements.

**Deliverables:**
- `src/sdi/patterns/__init__.py` with `build_pattern_catalog(records: list[FeatureRecord], config: SDIConfig, prev_catalog: PatternCatalog | None, partition: CommunityResult | None) -> PatternCatalog` public API
- `src/sdi/patterns/fingerprint.py` with `PatternFingerprint` class: structural hash computation from AST subtree descriptors (normalized — node types and structure, stripped of identifiers and literals), equality and comparison based on hash
- `src/sdi/patterns/catalog.py` with `PatternCatalog` class: groups fingerprints by category, identifies canonical pattern per category (most frequent shape), computes pattern entropy per category (count of distinct shapes), computes per-shape velocity (instance count delta vs. previous catalog), computes per-shape boundary spread (count of distinct boundaries each shape spans)
- `src/sdi/patterns/categories.py` with seven built-in category definitions and their tree-sitter query patterns for Python (other languages added per-adapter)
- `tests/fixtures/high-entropy/` with 10+ Python files containing 4+ error handling styles, 3+ data access patterns, 2+ logging styles
- `tests/unit/test_fingerprint.py`
- `tests/unit/test_catalog.py`

**[PM: Seven Built-in Category Names]**
The seven built-in categories to implement in `categories.py` are:

| Category name | Structural target |
|---|---|
| `error_handling` | `try`/`except`/`raise`/`finally` blocks and patterns |
| `data_access` | Function/method calls to data stores, ORM queries, cursor operations |
| `logging` | Log call sites (`logging.*`, `logger.*`, `log.*`) and their argument shapes |
| `async_patterns` | `async def`, `await`, `asyncio.gather`, coroutine entry points |
| `class_hierarchy` | Class definitions with base classes, `super()` call patterns |
| `context_managers` | `with` statement bodies and `__enter__`/`__exit__` pairs |
| `comprehensions` | List, dict, set, and generator comprehension expressions |

A category with no query for the current language returns no instances (empty list, not an error). Categories are referenced by their string name in config threshold overrides (e.g., `[thresholds.overrides.error_handling]`).

**Acceptance criteria:**
- Structurally equivalent AST subtrees (same node types and structure, different identifiers) produce identical fingerprints
- Structurally different AST subtrees produce different fingerprints
- Pattern entropy for `error_handling` in the `high-entropy` fixture is ≥ 4 (4+ distinct shapes)
- Canonical pattern per category is the shape with the highest instance count
- Per-shape velocity is null when `prev_catalog` is None (first snapshot)
- Per-shape velocity is an integer delta when a previous catalog exists
- Per-shape boundary spread is an integer count of distinct boundaries, or null when partition is None
- Categories with no detected instances report entropy 0, not an error
- `min_pattern_nodes` config filters out AST subtrees smaller than the threshold
- `PatternCatalog` serializes to and deserializes from JSON (for snapshot inclusion)
- `pytest tests/unit/test_fingerprint.py tests/unit/test_catalog.py` passes
- **[PM: added]** All seven category names listed above are registered in the category registry in `categories.py`; a lookup by unknown category name returns an empty result, not an exception

**Tests:**
- `tests/unit/test_fingerprint.py`: Identical AST shapes produce same hash, different shapes produce different hashes, identifier stripping works (same structure with different variable names = same hash), literal stripping works, minimum node threshold filters small patterns, empty AST subtree handled gracefully
- `tests/unit/test_catalog.py`: Catalog groups fingerprints by category correctly, entropy counts distinct shapes, canonical is most frequent shape, velocity computation (current minus previous instance counts), velocity is null on first snapshot, boundary spread counts distinct boundaries, empty category has entropy 0, catalog JSON round-trip, high-entropy fixture produces expected entropy values
- **[PM: added]** `tests/unit/test_catalog.py`: all seven category names in the registry resolve without error; lookup of an unregistered category name returns an empty instance list

**Watch For:**
- Structural hashing must normalize AST subtrees — node types are kept, identifier node values are replaced with a placeholder, literal values are replaced with a type token. The hash is of the normalized tree structure, not the raw source.
- The seven built-in categories need tree-sitter queries for each supported language. Start with Python queries; other languages are added in the adapter modules. A category with no query for the current language simply returns no instances.
- Boundary spread requires the partition from Stage 3 — if Leiden was skipped (graph too small), boundary spread is null for all shapes.
- Velocity is computed per-shape, not per-category. A category's overall "convention drift rate" is derived from velocity in Milestone 7.

**Seeds Forward:**
- `PatternCatalog` is included in the snapshot JSON — its serialization format becomes part of the snapshot schema
- Per-shape velocity feeds into the "convention drift rate" SDI dimension computation in Milestone 7
- Per-shape boundary spread is a raw measurement included in snapshots — it is never used for classification (Non-Negotiable Rule 4)
- The `categories.py` module's category registry pattern must support future extensibility (post-v1), though v1 ships with hardcoded categories only

---

## Archived: 2026-04-23 — Unknown Initiative

### Milestone 7: Snapshot Assembly, Delta Computation, and Trend Analysis
<!-- milestone-meta
id: "07"
status: "done"
-->


**Scope:** Build Stage 5 of the pipeline — assemble complete snapshots from all pipeline stage outputs, compute deltas between two snapshots across all four SDI dimensions, and compute trends across multiple snapshots. This is the "math" milestone — it takes raw stage outputs and produces the composite SDI metric.

**Deliverables:**
- `src/sdi/snapshot/assembly.py` with `assemble_snapshot(records, graph, metrics, community, catalog, config, commit_sha, timestamp) -> Snapshot` that combines all stage outputs into a `Snapshot` dataclass and writes JSON via atomic file operations
- `src/sdi/snapshot/delta.py` with `compute_delta(current: Snapshot, previous: Snapshot) -> DivergenceSummary` that computes all four SDI dimensions
- `src/sdi/snapshot/trend.py` with `compute_trend(snapshots: list[Snapshot], dimensions: list[str] | None) -> TrendData` for multi-snapshot trend analysis
- `tests/unit/test_delta.py`
- `tests/unit/test_trend.py`

**The four SDI dimensions in delta computation:**

| Dimension | Computation |
|---|---|
| `pattern_entropy_delta` | Per-category: current distinct shape count minus previous distinct shape count |
| `convention_drift_rate` | Net new patterns (shapes present now but not before) minus consolidated patterns (shapes present before but not now) across all categories |
| `coupling_topology_delta` | Composite of cycle count change, hub concentration change, max depth change, density change |
| `boundary_violation_velocity` | Count of new cross-boundary edges (imports crossing cluster boundaries) since previous snapshot |

**Acceptance criteria:**
- `assemble_snapshot()` produces a `Snapshot` with all required fields populated, including `snapshot_version`, `timestamp`, `commit_sha`, `config_hash`
- Snapshot JSON output is valid, self-contained, and includes all four dimension values
- `compute_delta()` returns null for all dimensions when `previous` is None (first snapshot)
- `compute_delta()` returns zero for all dimensions when current and previous are identical
- `compute_delta()` returns correct positive/negative values for known changes
- `compute_trend()` returns per-dimension time series data for the requested number of snapshots
- `compute_trend()` handles the case where the first snapshot in the range has null deltas
- Snapshot retention is enforced after assembly writes the file (calls `storage.enforce_retention()`)
- `pytest tests/unit/test_delta.py tests/unit/test_trend.py` passes

**Tests:**
- `tests/unit/test_delta.py`: Delta with no previous snapshot returns all nulls, delta with identical snapshots returns all zeros, pattern entropy delta computed correctly from known catalogs, convention drift rate computed correctly (new shapes minus lost shapes), coupling topology delta computed correctly from known graph metrics, boundary violation velocity computed from known partition changes, delta with incompatible snapshot version warns and returns null
- `tests/unit/test_trend.py`: Trend across 5 snapshots produces correct time series, trend with dimension filter returns only that dimension, trend with single snapshot (baseline) returns null series, trend correctly handles snapshots with null deltas at the start

**Watch For:**
- `convention_drift_rate` is NOT the same as `pattern_entropy_delta` — entropy delta measures the change in variety (how many distinct shapes), drift rate measures the change in conformity (net new shapes appearing minus shapes being consolidated). A codebase could have stable entropy (same number of shapes) but high drift rate (old shapes disappearing and new ones appearing at the same rate).
- `coupling_topology_delta` is a composite — define the weighting or normalization of its sub-components (cycle count change, hub concentration change, etc.) and document it. For v1, a simple sum of normalized sub-deltas is sufficient.
- `boundary_violation_velocity` requires comparing the current partition's cross-boundary edges to the previous partition's. If the partition itself changed (nodes moved to different clusters), new cross-boundary edges may appear without any new imports — this is intentional and correct (the boundary moved, so existing imports now cross it).
- `config_hash` in the snapshot should be a hash of the config values that affect analysis (not output formatting) — this allows detecting when config changes invalidate trend comparisons.

**Seeds Forward:**
- `DivergenceSummary` is included in every snapshot and is the primary output of `sdi diff`
- `TrendData` is the output of `sdi trend`
- The four dimension names (`pattern_entropy_delta`, `convention_drift_rate`, `coupling_topology_delta`, `boundary_violation_velocity`) become the enum values for `--dimension` flags in CLI commands
- Threshold checking in `sdi check` (Milestone 8) compares these delta values against config thresholds

---

---

## Archived: 2026-04-23 — Unknown Initiative

### Milestone 8: CLI Commands — snapshot, show, diff, trend, check, catalog
<!-- milestone-meta
id: "8"
status: "done"
-->


**Scope:** Wire the full analysis pipeline into the CLI commands. Implement `sdi snapshot` (full pipeline execution), `sdi show`, `sdi diff`, `sdi trend`, `sdi check`, and `sdi catalog` with all flags, output formats (text/json/csv), and exit codes. This is the integration milestone — each command orchestrates the pipeline stages from previous milestones.

**Deliverables:**
- `src/sdi/cli/snapshot_cmd.py` — full pipeline orchestration: parse → graph → leiden → patterns → assemble → write
- `src/sdi/cli/show_cmd.py` — read most recent snapshot, display summary
- `src/sdi/cli/diff_cmd.py` — compare two snapshots, display delta
- `src/sdi/cli/trend_cmd.py` — compute and display multi-snapshot trends with `--last`, `--dimension`, `--format csv`
- `src/sdi/cli/check_cmd.py` — CI gate with threshold checking and exit code 10
- `src/sdi/cli/catalog_cmd.py` — display pattern catalog with `--category` filter
- Rich-formatted text output for human mode (tables, colored deltas, sparklines for trends)
- JSON output for machine mode (valid, self-contained documents)
- CSV output for `sdi trend --format csv`
- Progress indicators on stderr (parsing progress bar, graph analysis spinner) via Rich

**Acceptance criteria:**
- `sdi snapshot` on `simple-python` fixture produces a valid snapshot JSON file in `.sdi/snapshots/`
- `sdi snapshot --commit HEAD` reads files at HEAD without modifying the working tree (uses `git show`)
- `sdi snapshot --output /tmp/test.json` writes to the specified path
- `sdi snapshot --format summary` prints human-readable summary to stdout
- `sdi show` displays the most recent snapshot summary
- `sdi show --format json | jq '.'` produces valid JSON
- `sdi diff` compares the two most recent snapshots
- `sdi diff SNAPSHOT_A SNAPSHOT_B` compares two specified snapshots
- `sdi trend --last 5` shows trend data for the 5 most recent snapshots
- `sdi trend --format csv` produces valid CSV output
- `sdi trend --dimension pattern_entropy` filters to one dimension
- `sdi check` exits 0 when all dimensions are within thresholds
- `sdi check` exits 10 when any dimension exceeds its threshold, printing which ones
- `sdi check --threshold 0.0` forces exit 10 on any non-zero change
- `sdi check --dimension boundary_violations` checks only one dimension
- `sdi catalog` displays all pattern categories with shape counts
- `sdi catalog --category error_handling` filters to one category
- All progress output goes to stderr; all data goes to stdout
- `--no-color` and `NO_COLOR=1` disable colored output
- `--quiet` suppresses progress indicators
- All existing unit tests continue to pass

**Tests:**
- `tests/integration/test_cli_output.py`: Capture stdout/stderr for each command, verify format correctness, verify exit codes, verify JSON validity, verify CSV validity
- `tests/integration/test_full_pipeline.py`: Run `sdi init` → `sdi snapshot` → `sdi show` → `sdi catalog` on `simple-python` fixture, verify end-to-end output
- `tests/unit/test_check_cmd.py`: Threshold comparison logic, per-dimension override application (including expired overrides), exit code 10 vs 0

**Watch For:**
- `sdi snapshot --commit REF` must use `git show REF:path` to read files — it must NEVER run `git checkout` or modify the working tree (Critical System Rule 9)
- Rich progress bars default to stdout — must explicitly use `Console(stderr=True)` for all Rich output
- JSON output from `--format json` must be a single valid JSON document, not streaming JSON lines
- `sdi check` is the only command that may exit with code 10 — ensure no other command accidentally returns 10
- When there are no previous snapshots, `sdi diff` should print a message ("only one snapshot exists") and exit 0, not error
- `sdi trend` with fewer snapshots than `--last N` should use all available snapshots, not error

**Seeds Forward:**
- CLI commands are the public API — flag names and output formats become the user-facing contract
- `sdi check` exit code 10 is used by CI pipelines and git hooks in Milestone 10
- `sdi snapshot --commit REF` capability enables the historical backfill scripting workflow (documented in post-v1 scope)

---
