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

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 9: Boundary Specification and Intent Divergence
<!-- milestone-meta
id: "9"
status: "done"
-->


**Scope:** Implement boundary specification management — parsing `.sdi/boundaries.yaml`, the `sdi boundaries` command with `--propose`, `--ratify`, and `--export` flags, and intent divergence computation (comparing detected Leiden partitions against ratified boundary specs). Extend `sdi init` to optionally propose and write a starter boundary spec.

**Deliverables:**
- `src/sdi/detection/boundaries.py` with `BoundarySpec` dataclass, YAML parsing via ruamel.yaml (comment-preserving), validation of required fields, intent divergence computation (files in wrong boundary, unexpected cross-boundary dependencies, layer direction violations)
- `src/sdi/cli/boundaries_cmd.py` with `--propose` (run Leiden and show proposed boundaries), `--ratify` (open in `$EDITOR`), `--export` (write to file), display modes (text/yaml)
- Update `src/sdi/cli/init_cmd.py` to optionally run inference and write starter `boundaries.yaml`
- Update `src/sdi/snapshot/assembly.py` to include intent divergence metrics in snapshots when a boundary spec exists
- Update `src/sdi/snapshot/delta.py` to include intent divergence changes in boundary violation velocity
- `tests/unit/test_boundaries.py`

**Acceptance criteria:**
- `BoundarySpec` correctly parses the YAML schema (modules, layers, allowed_cross_domain, aspirational_splits)
- Malformed boundary YAML exits with code 2 and descriptive error including line number
- Missing boundary spec is normal operation — no warning, no degraded mode, intent divergence metrics simply omitted from snapshot
- `sdi boundaries` displays the current ratified boundary map
- `sdi boundaries --propose` runs Leiden inference and displays proposed boundaries as a diff against the current spec
- `sdi boundaries --ratify` opens the boundary spec in `$EDITOR` for editing
- `sdi boundaries --export /tmp/boundaries.yaml` writes the current boundary map
- Intent divergence computation identifies: files assigned to wrong boundary (compared to spec), cross-boundary imports not in `allowed_cross_domain`, layer direction violations (e.g., domain importing from presentation)
- `allowed_cross_domain` entries suppress specific cross-boundary dependency flags
- `aspirational_splits` are tracked but do not affect current metrics
- ruamel.yaml preserves comments on round-trip when `--ratify` writes back
- `pytest tests/unit/test_boundaries.py` passes

**Tests:**
- `tests/unit/test_boundaries.py`: Parse valid boundary spec, reject spec with missing required fields, handle missing spec file gracefully (returns None, not error), intent divergence identifies misplaced files, intent divergence identifies unauthorized cross-boundary imports, intent divergence respects allowed_cross_domain exceptions, layer direction validation (downward = presentation → domain → infrastructure is OK, reverse is a violation), aspirational splits parsed and included in output, ruamel.yaml comment preservation verified on write-read cycle

**Watch For:**
- ruamel.yaml API differs from PyYAML — use `YAML(typ='rt')` (round-trip) for comment preservation
- `--ratify` opens `$EDITOR` — handle the case where `$EDITOR` is not set (fall back to `vi` on Unix, warn on Windows)
- Intent divergence computation must handle the case where the Leiden partition has different boundaries than the spec — this is expected (detection vs. ratified intent) and the difference is the measurement
- Layer direction validation: "downward" means a module in an upper layer may depend on a module in a lower layer, but not the reverse. The `layers.ordering` list defines the order from top to bottom.

**Seeds Forward:**
- Intent divergence metrics feed into `boundary_violation_velocity` in the snapshot delta — they add to (not replace) the partition-based boundary violation count
- The boundary spec `version` field enables schema evolution for boundary specs in future versions
- `aspirational_splits` could feed into a progress-toward-separation metric in post-v1

---

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 10: Caching and Performance Optimization
<!-- milestone-meta
id: "10"
status: "done"
-->


**Scope:** Implement the parse cache (keyed by file content hash) and fingerprint cache to make incremental snapshots near-instant when few files change. Add orphan cache cleanup. Verify performance targets (< 30s for 10K–100K LOC projects).

**Deliverables:**
- Parse cache in `src/sdi/parsing/__init__.py`: compute SHA-256 of file bytes, check `.sdi/cache/parse_cache/<hash>.json` before parsing, write cache entry after parsing
- Fingerprint cache in `src/sdi/patterns/fingerprint.py`: cache pattern fingerprint results per file content hash in `.sdi/cache/fingerprints/<hash>.json`
- Orphan cache cleanup: after snapshot capture, remove cache entries whose content hash does not correspond to any current file
- Performance validation against test fixtures at various scales

**Acceptance criteria:**
- Second run of `sdi snapshot` on an unchanged codebase completes significantly faster than the first (parse cache hit)
- Cache files are keyed by SHA-256 of file content — changing a file invalidates only that file's cache entry
- Cache is transparent — results are identical whether cache is hit or missed
- Orphan cache entries (files that no longer exist or have changed) are cleaned up after each snapshot
- Cache files use atomic writes
- `SDI_WORKERS=1` still works correctly with caching enabled
- Deleting `.sdi/cache/` entirely triggers a full re-parse with no errors (cold start)

**Tests:**
- `tests/unit/test_parse_cache.py`: Cache hit returns same FeatureRecord as fresh parse, cache miss triggers parse and writes cache, changed file invalidates cache (different hash), orphan cleanup removes stale entries, corrupt cache file triggers re-parse (not error)
- `tests/benchmarks/test_parsing_perf.py`: Measure parse time at 100, 1000, and 5000 file scales (synthetic), verify cache speedup
- `tests/benchmarks/test_leiden_perf.py`: Measure Leiden time at 100, 1000, 5000, and 10000 node graph scales

**Watch For:**
- SHA-256 hashing of file bytes is the cache key — not the file path. Renamed files with identical content hit the same cache entry (this is correct behavior).
- Cache files must be written atomically (tempfile + `os.replace`) just like snapshot files
- Orphan cleanup must not delete cache entries for files that are still present but unchanged — only entries whose hash is not found in the current file set
- Benchmark tests should NOT run in normal CI — gate them behind `pytest.mark.benchmark` or a separate test target

**Seeds Forward:**
- Caching makes `sdi snapshot` fast enough for CI use on medium projects (target: < 30s)
- The cache infrastructure (content-addressed storage with atomic writes) could be reused for other cached artifacts in post-v1

---

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 11: Git Hooks, CI Integration, and Shell Completion
<!-- milestone-meta
id: "11"
status: "done"
-->


**Scope:** Implement git hook installation (post-merge for automatic snapshots, pre-push for drift gate), document CI integration patterns, add Click shell completion support, and handle signal interrupts cleanly.

**Deliverables:**
- Git hook installation in `src/sdi/cli/init_cmd.py`: offer to install post-merge and pre-push hooks during `sdi init`
- Post-merge hook script: checks branch, runs `sdi snapshot --quiet`, exits 0 always
- Pre-push hook script: runs `sdi check`, blocks push on exit 10
- Signal handlers (SIGINT, SIGTERM) for clean shutdown: discard incomplete snapshots, clean up tempfiles
- Click shell completion setup for bash, zsh, and fish
- `docs/ci-integration.md` with examples for GitHub Actions, GitLab CI, and generic CI
- `tests/integration/test_git_hooks.py`

**Acceptance criteria:**
- `sdi init` prompts to install post-merge and/or pre-push hooks
- Hook installation is non-destructive: appends to existing hooks or creates new ones
- Post-merge hook runs `sdi snapshot --quiet` and always exits 0 (never blocks merges)
- Pre-push hook runs `sdi check` and blocks push only on exit 10
- Ctrl+C during `sdi snapshot` discards the incomplete snapshot (no partial files on disk)
- Shell completion works for bash, zsh, and fish via Click's built-in mechanism
- `docs/ci-integration.md` contains working CI config examples

**Tests:**
- `tests/integration/test_git_hooks.py`: Hook installation creates executable hook files, post-merge hook runs snapshot on merge, pre-push hook blocks push when threshold exceeded, hook installation appends to existing hooks (does not overwrite), hook scripts are valid shell scripts (shellcheck if available)

**Watch For:**
- Git hooks must be executable (`chmod +x`) — this is easy to forget on Unix
- Existing hooks: if `.git/hooks/post-merge` already exists, the SDI hook script must be appended (or the user must be warned), not overwritten
- SIGINT handling: Python's default SIGINT raises `KeyboardInterrupt` — the top-level handler in `cli/__init__.py` should catch this and exit cleanly
- Pre-push hook blocking pushes is opt-in only — clearly document this and don't install it by default
- Shell completion scripts should be documented in README/help but not auto-installed (users add them to their shell profile)

**Seeds Forward:**
- Git hooks are the primary automated integration point — they drive the "run SDI on every merge" workflow
- CI integration documentation establishes the deployment pattern for SDI in real projects
- The post-v1 GitHub Actions marketplace action would wrap the patterns documented in `docs/ci-integration.md`

---

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 12: Integration Tests, Polish, and Packaging
<!-- milestone-meta
id: "12"
status: "done"
-->


**Scope:** Comprehensive integration testing (multi-snapshot lifecycle, evolving fixture), the `evolving` test fixture with progressive drift across git commits, end-to-end verification of all CLI commands, CI workflow files (`.github/workflows/ci.yml`), and final packaging verification (wheel build, entry point, extras).

**Deliverables:**
- `tests/fixtures/evolving/` — a git repository fixture with 5+ commits that introduce progressive structural drift (built by `tests/fixtures/setup_fixture.py` script)
- `tests/integration/test_multi_snapshot.py` — full lifecycle: init → snapshot → modify → snapshot → diff → trend → check
- `tests/integration/test_full_pipeline.py` — expanded to cover all fixture types
- `tests/integration/test_cli_output.py` — expanded to cover all commands with all output formats
- `.github/workflows/ci.yml` — lint (ruff), type check (mypy), unit tests, integration tests, coverage report
- `.github/workflows/benchmarks.yml` — performance benchmarks triggered on release tags
- Final `pyproject.toml` verification: wheel builds correctly, `sdi` entry point works from a clean install, all extras install correctly

**Acceptance criteria:**
- `tests/fixtures/setup_fixture.py` creates the evolving fixture reproducibly (creates a temp git repo with scripted commits)
- Multi-snapshot lifecycle test passes: init → snapshot → modify fixture (add a new pattern variant) → snapshot → diff (shows correct delta) → trend (shows two data points) → check (threshold comparison)
- All CLI commands produce valid output in all formats (text, json, csv where applicable)
- All exit codes match their documented semantics (0, 1, 2, 3, 10)
- CI workflow runs lint + type check + unit tests + integration tests on push/PR
- Benchmark workflow runs on release tags only
- `python -m build` produces a valid wheel and sdist
- `twine check dist/*` passes
- Coverage report shows ≥ 80% unit test coverage
- All tests pass on Python 3.10, 3.11, and 3.12

**Tests:**
- `tests/integration/test_multi_snapshot.py`: Full lifecycle on evolving fixture — init, snapshot (baseline with null deltas), modify fixture, snapshot (deltas computed), diff (shows changes), trend (two-point series), check (with tight thresholds to trigger exit 10, with relaxed thresholds to pass)
- `tests/integration/test_full_pipeline.py`: Run full pipeline on simple-python, multi-language, and high-entropy fixtures — verify output structure and values
- `tests/integration/test_cli_output.py`: Every command with `--format text`, `--format json`; `sdi trend` with `--format csv`; verify stderr has no data leakage

**Watch For:**
- The evolving fixture requires a real git repository — use `subprocess` to run `git init`, `git add`, `git commit` in a temp directory. Clean up after test run.
- Python version matrix (3.10, 3.11, 3.12) may surface issues with `tomllib` availability (3.10 needs `tomli`), type hint syntax differences, or tree-sitter API changes
- Coverage threshold of 80% unit test coverage — if this is hard to hit, focus coverage on the delta computation, config validation, and pattern fingerprinting modules (highest bug risk)
- mypy with `disallow_untyped_defs = true` will require type annotations on all public functions — ensure this has been maintained throughout all milestones

**Seeds Forward:**
- This milestone produces a shippable v0.1.0 — the complete SDI tool ready for early adopter feedback
- The CI workflow becomes the ongoing quality gate for all future development
- The evolving fixture becomes the canonical test for trend computation accuracy

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 13: Shell Language Discovery and Adapter Foundation
<!-- milestone-meta
id: "13"
status: "done"
-->


**Scope:** Add first-class shell parsing support to SDI's Stage 1 pipeline so shell scripts are discovered, parsed, and represented as FeatureRecords with deterministic behavior and graceful degradation when grammar dependencies are missing.

**Deliverables:**
- Shell grammar dependency wiring:
  - Add `tree-sitter-bash` (canonical PyPI package, no version pin needed beyond what `tree-sitter>=0.24` constrains) to the `all` optional extra in `pyproject.toml` (alongside the other `tree-sitter-*` packages at `pyproject.toml:42-52`).
  - Add `tree-sitter-bash` to the `[[tool.mypy.overrides]] module = [...]` list at `pyproject.toml:72-74` so missing type stubs do not fail `mypy`.
  - Import failure handling is automatic: `_register_adapters` in `src/sdi/parsing/_runner.py:22-44` already wraps adapter imports in `try/except ImportError` and emits a `[warning]` to stderr. The shell adapter only needs to be appended to the `_adapter_modules` list — no additional warning code required.
- Discovery updates in `src/sdi/parsing/discovery.py`:
  - Extend `_EXTENSION_TO_LANGUAGE` (`discovery.py:10-20`) with: `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash` → `"shell"`. Do **not** map `.fish`; fish syntax is incompatible with `tree-sitter-bash` and parse failures would corrupt downstream analysis. `.fish` files fall into the existing "no grammar" warning path automatically.
  - Add shebang-based detection for extensionless scripts via a private helper `_detect_shell_shebang(path: Path) -> bool` in `discovery.py`. Behaviour:
    - **Trigger:** only for files where `detect_language(path)` returns `None` AND `path.suffix == ""` AND the executable bit is set (`path.stat().st_mode & 0o111 != 0`). Skip otherwise — never read content for files that already have a known/unknown extension.
    - **Read:** open in binary mode and read at most 256 bytes (one `read(256)`). Decode with `errors="replace"`. Inspect only the first line.
    - **Match rule:** the first line must start with `#!` and the remainder must contain a path component (split on `/` and whitespace) equal to one of: `sh`, `bash`, `zsh`, `ksh`, `dash`, `ash`. Reject `python`, `python3`, `node`, `ruby`, `perl`, `awk`, `sed`, etc. For `#!/usr/bin/env <cmd>`, take `<cmd>` (the first whitespace-separated token after `env`) and apply the same allow-list.
    - **Integration:** call `_detect_shell_shebang` inside `discover_files` after the existing `detect_language` check; on True, append `(path, "shell")` to results. Apply gitignore/exclude filters before the shebang check (mirror existing order).
  - File-content I/O cost is bounded: only extensionless executable files trigger a `read(256)`. Unsupported text files (no extension, no exec bit, or non-shell shebang) remain silently ignored — no warnings.
- New adapter implementation in `src/sdi/parsing/shell.py` (model after `src/sdi/parsing/go.py`):
  - Implement `ShellAdapter(LanguageAdapter)` using `tree_sitter_bash`. `language_name` returns `"shell"` for all supported extensions. `file_extensions = frozenset({".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash"})`.
  - Use the lazy `_PARSER` singleton pattern from `go.py:22-30`. Reuse helpers from `_lang_common.py`: `_structural_hash`, `_location`, `_walk_nodes`, `count_loc`.
  - **Imports / includes** — populate `FeatureRecord.imports` from `command` AST nodes whose `command_name` is `source` or `.`, with a single literal-string argument:
    - Resolve the literal path to a repo-relative POSIX string. If the literal is absolute or starts with `/`, attempt `Path(literal).resolve().relative_to(repo_root)`; on failure, drop the import.
    - If the literal is relative (`./common.sh`, `../lib/util.sh`, `common.sh`), resolve relative to the **importing file's directory**, then `relative_to(repo_root)`. Drop on failure.
    - Skip dynamic forms entirely: any argument containing `$`, backticks, command substitution `$(...)`, glob metacharacters, or word-splitting whitespace. Static literal only.
    - Output format matches what `graph/builder.py` already consumes for file-based languages (the same convention Python uses for resolved relative imports): a repo-relative POSIX path string, e.g. `"src/lib/util.sh"`. Unresolved imports are silently dropped (consistent with existing adapters).
  - **Symbols** — extract from `function_definition` nodes. The name is the `name` field text (`child_by_field_name("name")`). Both shell forms (`foo() { ... }` and `function foo { ... }`) parse to the same `function_definition` node — no special-casing needed. No namespacing; append the bare name to `symbols`.
  - **Pattern instances** — write a private module `src/sdi/parsing/_shell_patterns.py` mirroring `_python_patterns.py` (custom AST walker; do **not** use `categories.py` query strings — see Watch For). Detect:
    - `error_handling`:
      - `command` nodes with `command_name == "set"` whose argument list contains any of `-e`, `-u`, `-o pipefail`, `-eu`, `-eo`, `-uo`, `-euo`, or any `-` flag combination including `e`, `u`, or starting with `-o`.
      - `command` nodes with `command_name == "trap"` whose last argument is `ERR`, `EXIT`, `INT`, `TERM`, or `HUP`.
      - `command` nodes with `command_name in {"exit", "return"}` whose first argument is a numeric literal `!= "0"`.
      - `list` nodes (the `||` and `&&` constructs) whose right side is a `command` with `command_name in {"exit", "return", "false"}`.
    - `logging`:
      - `command` nodes with `command_name in {"echo", "printf", "logger", "tee"}`.
    - **Structural hash composition for shell:** because `command` nodes share the same node type regardless of `command_name`, fold `command_name` into the structural fingerprint when emitting an instance. Implement a `_shell_structural_hash(node)` helper in `_shell_patterns.py` that, for `command` nodes, prepends `command_name` text to the serialization before hashing; falls back to `_lang_common._structural_hash` for non-command nodes. This keeps `set -e`, `trap ERR`, and `exit 1` as distinct shapes.
  - **Pattern category registration** — add a decorative `_SHELL_QUERIES: dict[str, str] = {}` plus a shell entry in the per-language registry inside `src/sdi/patterns/categories.py:46-122` for parity. Leave `_SHELL_QUERIES` empty in v1 — the actual extraction lives in `_shell_patterns.py`. This keeps `categories.py` aware of shell as a registered language without misleading query strings.
- Runner registration in `src/sdi/parsing/_runner.py`:
  - Append `("shell", "sdi.parsing.shell", "ShellAdapter")` to `_adapter_modules` in `_register_adapters` (`_runner.py:28-35`). No other changes needed — the existing `try/except ImportError` block at lines 37-44 produces the warning automatically.
- Parse cache (`src/sdi/parsing/_parse_cache.py`):
  - **No changes required.** The cache is keyed on file content SHA-256 and is language-agnostic; shell `FeatureRecord`s round-trip through the existing read/write paths automatically. Mention only to pre-empt over-engineering.
- Test conftest (`tests/conftest.py`):
  - Add `_has_shell_adapter()` and `requires_shell_adapter` markers mirroring `_has_python_adapter` / `requires_python_adapter` at `conftest.py:28-56`. Every shell-touching test must be gated by `requires_shell_adapter`.
- Fixture and test coverage:
  - Add `tests/fixtures/simple-shell/` with **3 scripts** (≈10–20 LOC each):
    - `deploy.sh`: starts with `set -euo pipefail`, contains `source ./lib/util.sh`, defines one function, has one `echo` and one `logger` call, includes one `trap cleanup ERR`.
    - `lib/util.sh`: defines two functions, contains one `printf`-based logging call, no error handling.
    - `extensionless-script` (no extension, exec bit set, shebang `#!/usr/bin/env bash`): defines one function and one `echo`.
  - Add `tests/unit/test_shell_adapter.py` (gated by `requires_shell_adapter`):
    - import/include extraction: literal `source ./x.sh` and `. ./x.sh` resolve to repo-relative paths.
    - dynamic-source rejection: `source "$DIR/x.sh"`, `source $(which foo)`, and `source ${LIB}/x.sh` produce zero imports.
    - function symbol extraction: both `foo() { ... }` and `function foo { ... }` add `foo` to `symbols`.
    - error_handling instances: `set -e`, `set -euo pipefail`, `trap cleanup ERR`, and `exit 1` each produce one instance with distinct `ast_hash` values.
    - logging instances: `echo`, `printf`, and `logger` calls each produce one `logging` instance with distinct `ast_hash` values.
    - empty file → zero instances, zero imports, zero symbols, no exception.
    - syntactically broken script → adapter emits warning via `parse_file_safe`, returns `None`, no exception escapes.
    - structural-hash stability: parsing the same script bytes twice yields identical `ast_hash` values for every instance.
  - Extend `tests/unit/test_discovery.py`:
    - extensions `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash` map to `"shell"`.
    - `.fish` does **not** map to `"shell"` (returns `None` from `detect_language`).
    - extensionless executable file with `#!/usr/bin/env bash` is discovered as `("shell", path)`.
    - extensionless executable file with `#!/usr/bin/env python3` is **not** discovered (returns nothing).
    - extensionless file without exec bit but with `#!/bin/bash` shebang is **not** discovered.
    - file with `.txt` extension and `#!/bin/bash` shebang is **not** discovered (extension takes precedence; no content read).
  - Extend `tests/integration/test_full_pipeline.py`:
    - Add a test class gated by `requires_shell_adapter` that points `parse_repository` at `tests/fixtures/simple-shell/` and asserts `language_breakdown["shell"] == 3`, the expected `symbols` count, and at least one `error_handling` and one `logging` pattern instance in the resulting catalog.
- Documentation:
  - Add a one-line entry under the "Unreleased" / next-version heading in `CHANGELOG.md`: `Added: shell language support (.sh/.bash/.zsh/.ksh and shebang detection) via tree-sitter-bash.`

**Acceptance criteria:**
- `sdi snapshot` on `tests/fixtures/simple-shell/` (no custom config) reports `language_breakdown["shell"] == 3` and produces a non-empty pattern catalog.
- Extensionless executable scripts with allow-listed shell shebangs are discovered as `("shell", path)`; non-shell shebangs are ignored without warning.
- With `tree-sitter-bash` not installed, `_register_adapters` emits one `[warning] Shell adapter unavailable: ...` to stderr and the snapshot completes (no crash) when other grammars are available.
- `FeatureRecord.language == "shell"` for every parsed shell file regardless of extension.
- Static `source` / `.` imports resolve to repo-relative POSIX paths; dynamic forms produce zero imports and no warnings.
- All new unit and integration tests pass on Python 3.10, 3.11, and 3.12.
- `mypy src/sdi/` passes with `tree-sitter-bash` either present or absent.
- No regressions: existing fixture-based snapshot/catalog tests for Python/TS/JS/Go/Java/Rust produce byte-identical `language_breakdown` keys for non-shell fixtures.

**Tests:** (full enumerated assertions are listed under "Fixture and test coverage" above; this section is a checklist of the test files touched)

- `tests/unit/test_discovery.py` — six new cases (extensions, fish exclusion, shebang positive, shebang negative on python, no-exec-bit, extension-takes-precedence).
- `tests/unit/test_shell_adapter.py` — eight cases (imports, dynamic rejection, both function forms, four error_handling shapes, three logging shapes, empty file, broken script, hash stability).
- `tests/integration/test_full_pipeline.py` — one new class gated by `requires_shell_adapter` asserting `language_breakdown["shell"] == 3` and presence of `error_handling` + `logging` instances.

**Watch For:**
- **Do not use `categories.py` query strings for extraction.** The `_PYTHON_QUERIES` strings at `src/sdi/patterns/categories.py:46-82` are decorative and unused at runtime — actual extraction lives in per-language walker modules (`_python_patterns.py` and the `_extract_patterns` function in `go.py:156-183`; Java/Rust/JS/TS adapters follow the same custom-walker convention with no query strings registered at all). Follow that convention for shell: walker code in `_shell_patterns.py`, `_SHELL_QUERIES = {}` left empty.
- **`set -e` family fingerprint coarseness.** Tree-sitter-bash represents shell builtins as `command` nodes; without folding `command_name` into the structural hash, every `set -e` / `set -u` / `set -o pipefail` collapses to the same shape. The `_shell_structural_hash` helper specified in the adapter section is mandatory, not optional — otherwise `error_handling` entropy will under-count.
- **Shebang detection is the only file-content I/O during discovery.** Bound it: extensionless files only, exec bit required, 256-byte read max, first line only. Any cost growth here regresses parse latency.
- **Allow-list shebang interpreters strictly.** Match path tokens, not substrings — otherwise `#!/usr/bin/env bashbrew` would be miscategorized. Use `Path(interp).name in {"sh","bash","zsh","ksh","dash","ash"}`.
- **Static-only `source` resolution.** Drop any `source` argument containing `$`, backticks, `$(...)`, glob chars, or whitespace splits. Capturing dynamic forms produces phantom edges and breaks reproducibility.
- **`.fish` is intentionally unsupported.** Fish syntax differs from POSIX/bash and tree-sitter-bash will produce malformed ASTs. Map `.fish` to no language so it surfaces in the existing "no grammar" warning rather than corrupting analysis silently.
- **Determinism guarantees:** no shell execution, no env-var expansion, no filesystem traversal beyond the parsed file's directory.

**Seeds Forward:**
- Enables SDI coverage for shell-heavy repos (high-impact for Tekhton-scale script surfaces).
- Establishes shell AST substrate needed for richer pattern fingerprints and better drift signal quality in Milestone 14.
- Unblocks future support for script-centric boundary inference in ops/infrastructure codebases.

---

---

## Archived: 2026-04-24 — Unknown Initiative

### Milestone 14: Shell Pattern Quality, Trend Calibration, and Rollout
<!-- milestone-meta
id: "14"
status: "done"
-->


**Scope:** Improve shell signal quality beyond raw parsing by calibrating pattern extraction, validating trend behavior on shell-heavy histories, and documenting operational guidance so shell support is trustworthy for gates and remediation workflows. Builds directly on M13's `ShellAdapter` and `_shell_patterns.py`; this milestone extends — not replaces — those modules.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 4, SDI never classifies code as "good" or "bad." All language in this milestone uses *measurement* phrasing: "structurally distinct shapes," "additional categories detected," "broader command-name coverage." Phrasing like "robust vs ad-hoc," "best practice," or "quality" must not appear in code, comments, tests, or docs delivered by this milestone.

**Deliverables:**
- Pattern quality expansion in `src/sdi/parsing/_shell_patterns.py` (the walker module introduced in M13). All additions emit `(category, ast_hash, location)` tuples via the existing `_shell_structural_hash` helper, which folds `command_name` into the structural fingerprint so distinct command names produce distinct shapes.
  - **`error_handling` — broaden the M13 set so the following structures each produce a distinct `ast_hash`:**
    - `set` invocations: any flag string containing `e`, `u`, or `o pipefail` (M13 baseline).
    - `trap <handler> <signal>` for any signal in `{ERR, EXIT, INT, TERM, HUP, QUIT}`.
    - `if_statement` whose immediate body contains `exit` or `return` with non-zero literal.
    - `list` (`||` / `&&`) right-hand side ending in `exit`/`return`/`false`.
    - `command` with `command_name == "exit"` or `"return"` and a non-zero numeric literal first argument.
    - `command_substitution` whose result is consumed by `[ -z ... ]` / `[ -n ... ]` / `[[ ... ]]` test expressions (defensive existence checks).
    - **No quality ranking.** Every structurally distinct shape is its own catalog entry; entropy rises with shape count, full stop.
  - **`async_patterns` — extend the existing category to shell-flavoured concurrency. Decision noted explicitly: catalog entropy is per-category, not per-language; mixing shell `&` shapes with Python `async def` shapes in the same category is intentional and consistent with the language-agnostic catalog model.** Detect:
    - Any command terminated by `&` (background job): the parent node is `command` with `background = "&"` field, or a `pipeline` whose final element is followed by `&`.
    - `command_name == "wait"` with or without arguments.
    - `pipeline` nodes with three or more stages (fan-out heuristic): a structural-only count, no semantic judgment.
    - `command_name in {"xargs", "parallel"}` with a `-P` / `--max-procs` flag literal.
  - **`data_access` — populate `command_name` allow-list:**
    - `{curl, wget, jq, yq, psql, mysql, mysqldump, pg_dump, redis-cli, mongo, mongosh, sqlite3, aws, gcloud, kubectl, az, doctl, terraform}`.
    - Detection rule: `command` node whose `command_name` text matches the allow-list. The structural hash includes `command_name` (M13 helper), so `curl` and `psql` are distinct shapes — verify in tests.
  - **`logging` — populate `command_name` allow-list:**
    - `{echo, printf, logger, tee}` (the M13 baseline) plus `>&2` redirection patterns: any `redirected_statement` whose redirect target is `&2`. Treat the redirect form as a separate shape from bare `echo`.
  - **Measurement-only semantics — explicit guard:** any new helper, comment, test name, or docstring containing the words "good," "bad," "best practice," "robust," "ad-hoc," "proper," or "quality" is a defect. The PR description must affirm this audit was performed.
- Shell-focused fixture evolution:
  - Add `tests/fixtures/shell-heavy/` with **8–12 scripts (≈20–60 LOC each)** spanning three subdirectories: `deploy/` (3-4 scripts), `ci/` (3-4 scripts), `ops/` (2-4 scripts). Aggregate content guarantees:
    - **≥ 4 distinct `error_handling` shapes** (e.g., `set -euo pipefail`, `trap ... ERR`, `cmd || exit 1`, `if ! foo; then return 1; fi`).
    - **≥ 3 distinct `data_access` shapes** (e.g., `curl`, `psql`, `kubectl`).
    - **≥ 2 distinct `logging` shapes** (e.g., `echo`, `>&2` redirect).
    - **≥ 2 distinct `async_patterns` shapes** (e.g., backgrounded `&`, `wait`, `xargs -P`).
    - **≥ 2 cross-script `source` imports** to exercise the graph builder.
  - Add `tests/fixtures/evolving-shell/` as a **new dedicated fixture** (do not modify the existing `tests/fixtures/evolving/` Python fixture). Include a `setup_fixture.py` that materializes 4 commits in a temp git repo:
    - **C1 (baseline):** 5 shell scripts, 1 `error_handling` shape (`set -e` only), 1 `logging` shape, no `async_patterns`.
    - **C2 (drift):** add 2 new `error_handling` shapes (`trap ... ERR`, `cmd || exit 1`) and 1 new `logging` shape (`>&2` redirect). Net new shapes: 3.
    - **C3 (consolidation):** refactor C2's three error_handling shapes down to two by replacing all `cmd || exit 1` instances with `set -euo pipefail` at file head. Net shape change: −1.
    - **C4 (regression):** introduce a 4th `error_handling` shape and a new `async_patterns` shape (`xargs -P 4`). Net new shapes: 2.
  - Mirror M13's `simple-shell/` style for file conventions (extension `.sh`, exec bit set on entrypoint scripts, shebangs `#!/usr/bin/env bash`).
- Trend and threshold validation — add `tests/integration/test_shell_evolving.py` (gated by `requires_shell_adapter`) that runs `setup_fixture.py` and walks C1→C4, asserting:
  - **C1 snapshot:** `divergence.pattern_entropy_delta is None` (first snapshot baseline). All four delta dimensions are `None`, not `0`.
  - **C1→C2 (`sdi diff`):** `pattern_entropy_delta["error_handling"] >= 2`, `pattern_entropy_delta["logging"] >= 1`, `convention_drift_rate > 0` (net new shapes).
  - **C2→C3 (`sdi diff`):** `pattern_entropy_delta["error_handling"] <= -1`, `convention_drift_rate < 0` (consolidation — old shapes lost).
  - **C3→C4 (`sdi diff`):** `pattern_entropy_delta["error_handling"] >= 1`, `pattern_entropy_delta["async_patterns"] >= 1`.
  - **`sdi trend`** across all four snapshots returns a 4-point series with the correct sign sequence: `[null, +, -, +]` for `convention_drift_rate`.
  - **`sdi check` exit codes:** with default thresholds, C1→C2 exits `10` (threshold exceeded — drift rate > `3.0`); C2→C3 exits `0`; C3→C4 exits `0` (within bounds with default thresholds, since 2 new shapes < `3.0`).
  - All numeric thresholds above use the defaults from `src/sdi/config.py`. If those defaults change, update assertions accordingly — do not hardcode numbers that drift from config.
- Documentation and DX updates — concrete content checklist:
  - **`README.md`** — under the existing language-support section, add a "Shell" subsection covering:
    1. Supported extensions: `.sh, .bash, .zsh, .ksh, .dash, .ash`. Note `.fish` is not supported.
    2. Shebang detection: extensionless executable files with `#!/usr/bin/env bash` (and the allow-list from M13) are picked up automatically.
    3. Installation: `pip install 'sdi[all]'` includes `tree-sitter-bash`.
    4. Categories detected for shell: `error_handling`, `logging`, `data_access`, `async_patterns` (with one-line descriptions matching `categories.py`).
    5. Known limits: dynamic `source` paths skipped, heredoc bodies not pattern-matched, fish syntax unsupported, parse failures emit a per-file warning and skip.
  - **`docs/ci-integration.md`** — add:
    1. A worked example invoking `sdi check` against a shell-heavy repo.
    2. A concrete TOML override block for shell-script-heavy projects:
       ```toml
       [thresholds.overrides.error_handling]
       pattern_entropy_rate = 6.0
       expires = "2026-Q4"
       reason = "Migrating ops scripts from set -e to explicit error traps"

       [thresholds.overrides.async_patterns]
       pattern_entropy_rate = 5.0
       expires = "2026-12-31"
       reason = "Pipeline parallelism rollout in deploy/"
       ```
    3. A note that default thresholds tuned for application code may be too strict for script-heavy repos and overrides are the supported relief valve.
  - **`CHANGELOG.md`** — entry under "Unreleased": `Added: shell pattern quality (broader error_handling, async_patterns, data_access, logging coverage), shell-heavy fixtures, and CI integration docs.`
- Performance and cache verification:
  - Add a unit test in `tests/unit/test_parse_cache.py` (or new `test_parse_cache_shell.py`) verifying: parse a shell file once → write cache; parse the same bytes → read returns the cached `FeatureRecord` (assert no parser invocation by mocking `_get_parser` or by timing). No `_parse_cache.py` source changes expected — this confirms language-agnostic behaviour holds for shell.
  - Add a benchmark case to `tests/benchmarks/test_parsing_perf.py` parameterised on `language="shell"` that:
    - Generates 100 synthetic shell scripts of ≈50 LOC each in a temp dir.
    - Asserts cold-parse runtime < **1.5s** on a 4-core CI runner (`SDI_WORKERS=4`).
    - Asserts cache-hit rerun < **0.3s** on the same set.
    - Numbers are budgets, not contracts: tune once the benchmark runs locally, but the budget must be hard-coded so regressions surface.

**Acceptance criteria:**
- Shell pattern instances appear in `PatternCatalog` for all four categories (`error_handling`, `logging`, `data_access`, `async_patterns`) when present in source. Identical bytes parsed twice produce identical `ast_hash` sets (reproducibility).
- `sdi trend` on `tests/fixtures/evolving-shell/` (4 commits) returns 4 data points; the `convention_drift_rate` series follows the sign sequence `[null, +, -, +]`.
- `sdi diff` between any two `evolving-shell` commits returns the deltas enumerated in the trend/threshold validation section above (numeric assertions, not "as expected").
- `sdi check` exits `10` for the C1→C2 transition and `0` for C2→C3 and C3→C4 with default thresholds.
- Documentation acceptance is checklist-based, not subjective: `README.md` includes the 5 enumerated items in the docs-update section; `docs/ci-integration.md` includes the worked example and the literal TOML override snippet; `CHANGELOG.md` has the new entry.
- Benchmark assertions pass: cold parse < 1.5s, cache rerun < 0.3s on 100×50-LOC synthetic shell scripts.
- **No regressions:** existing fixture-based tests for Python/TS/JS/Go/Java/Rust produce byte-identical `language_breakdown` and `pattern_catalog` keys (excluding new shell entries) compared to a pre-M14 reference run. Capture the reference by running the suite before any M14 changes; commit the reference JSON if needed for diffing.
- **Philosophy compliance:** grep of all M14 deliverables (source, tests, docs) returns zero hits for `\b(robust|ad-hoc|good|bad|best practice|proper|quality)\b` in pattern-related contexts. The PR description must include the grep result.

**Tests:** (gate every shell-touching test with `requires_shell_adapter` from `tests/conftest.py`)

- `tests/unit/test_shell_adapter.py` — extend with:
  - one case per new `error_handling` shape from the deliverables list (5 cases beyond M13's 4); each asserts a unique `ast_hash`.
  - one case per `async_patterns` rule (background `&`, `wait`, fan-out pipeline, `xargs -P`).
  - one case asserting `data_access` allow-list covers `curl`, `psql`, `kubectl`, `jq` with distinct `ast_hash` per command.
  - one case for `logging` `>&2` redirect producing a different `ast_hash` than bare `echo`.
  - reproducibility: parsing the `tests/fixtures/shell-heavy/` tree twice yields identical `(category, ast_hash)` multisets.
- `tests/unit/test_catalog_velocity_spread.py` — extend with two cases:
  - **velocity:** building a catalog from `evolving-shell` C2 with C1 as `prev_catalog` produces `velocity[shape] == 1` for each newly introduced shell shape and `velocity[shape] == 0` for unchanged shapes.
  - **boundary spread:** when the same shell `error_handling` shape appears in two different Leiden clusters of the `shell-heavy` fixture, `boundary_spread[shape] == 2`.
- `tests/integration/test_shell_evolving.py` — new file (referenced in deliverables) running the full `init → snapshot×4 → diff → trend → check` workflow against `evolving-shell`. Assertions enumerated in the trend/threshold validation deliverable.
- `tests/benchmarks/test_parsing_perf.py` — new `test_shell_parse_perf_cold` and `test_shell_parse_perf_cached` cases with the budgets above.

**Watch For:**
- **Phrasing audit is enforced.** "Robust vs ad-hoc," "best practice," "good/bad" phrasing in any deliverable file violates Non-Negotiable Rule 4. The PR must include `git grep -nE '\b(robust|ad-hoc|good|bad|best practice|proper|quality)\b' src/ tests/ docs/ README.md CHANGELOG.md` output showing zero pattern-related hits.
- **`async_patterns` mixing across languages is intentional.** The same category aggregates Python `async def` and shell `&` shapes. Reviewers may flag this as a smell; the milestone explicitly endorses it. Do not split the category to "fix" the perceived overlap — that would break the language-agnostic catalog model.
- **`command_name` must be folded into the structural hash for `command` nodes.** This is the M13 helper `_shell_structural_hash`; without it, `curl`, `psql`, and `kubectl` collapse to one shape and `data_access` entropy becomes meaningless. Verify each new test case asserts distinct hashes between distinct command names.
- **Overfitting risk.** Detection rules are structural and command-name-based — never path-based, file-name-based, or content-keyword-based. Rules that key off `deploy.sh` or `# CI script` belong elsewhere.
- **Generated shell wrappers** (e.g., autotools, hand-rolled codegen output) inflate entropy and convention drift. Document in `README.md` that users should add such directories to `[core] exclude` patterns; do not attempt auto-detection in v1.
- **Fish/zsh edge cases.** `tree-sitter-bash` parses POSIX/bash cleanly; zsh-specific constructs (e.g., `=()` process substitution syntax variants) may produce ERROR nodes. The adapter already returns `None` on parse exceptions via `parse_file_safe`; do not add zsh-specific handling.
- **Threshold defaults vs. script-heavy repos.** The override examples in `ci-integration.md` are the only sanctioned relief mechanism — never lower default thresholds to accommodate scripts.
- **Benchmark numbers are CI-runner dependent.** The 1.5s / 0.3s budgets target a 4-core x86_64 GitHub-Actions-class runner. If running on slower hardware, document the local baseline in the PR description but keep the committed budget at the stated values.

**Seeds Forward:**
- Makes shell support production-ready for CI gates rather than exploratory.
- Improves remediation usability by turning shell drift into interpretable catalog and trend output.
- Provides a template for adding future language support with two-step rollout: ingestion foundation, then signal calibration.

---

---

## Archived: 2026-04-26 — Unknown Initiative

### Milestone 15: Shell Dependency Edge Resolution in Graph Builder
<!-- milestone-meta
id: "15"
status: "done"
-->


**Scope:** Wire shell adapter output into the dependency graph so static `source` / `.` directives produce real edges. M13 shipped per-file extraction of resolved repo-relative POSIX paths in `FeatureRecord.imports`. `build_dependency_graph` (`src/sdi/graph/builder.py:411-421`) currently dispatches resolution two ways — TS/JS path-based and Python dotted-module-key — and shell falls into the Python branch where its path-shaped strings never match the module map. Result: shell-heavy repos report ~0 edges, ~N components, and ~N clusters, which makes coupling, community detection, and boundary-violation signals all degenerate. This milestone closes that gap with a third dispatch arm.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 3, same commit + same config + same boundaries must produce the same snapshot. The extension fallback added here must be deterministic — a fixed allow-list, ordered, never iteration over a set. Per Rule 9, no command modifies the working tree; the graph builder reads only from the in-memory `path_to_id` set, never the filesystem. The shell adapter already pre-resolves source paths against the importing file's directory; the graph builder's job is *lookup only*, never path math.

**Deliverables:**
- New shell resolver in `src/sdi/graph/builder.py`:
  - Add module-level constants near the existing `_JS_TS_LANGS` (`builder.py:38`):
    ```python
    _SHELL_LANGS: frozenset[str] = frozenset({"shell"})
    _SHELL_EXTENSIONS_FOR_FALLBACK: tuple[str, ...] = (".sh", ".bash")
    ```
    Order is significant — `.sh` is checked before `.bash`. Do **not** include `.zsh`, `.ksh`, `.dash`, or `.ash` in the fallback tuple; those are accepted as primary file extensions (per M13) but adding them as fallback targets produces phantom edges in mixed-shebang repos.
  - Add a `_resolve_shell_import(import_str: str, path_set: frozenset[str]) -> str | None` helper:
    1. Fast path: if `import_str in path_set`, return `import_str`.
    2. Fallback: if the literal does not end in any of `(".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash")`, attempt `import_str + ext` for each `ext` in `_SHELL_EXTENSIONS_FOR_FALLBACK`, returning the first match.
    3. Otherwise return `None`.
  - In `build_dependency_graph` (the per-record loop at `builder.py:412-435`), dispatch shell records *before* the existing Python branch:
    ```python
    is_shell = record.language in _SHELL_LANGS
    is_js_ts = record.language in _JS_TS_LANGS

    for import_str in record.imports:
        if is_shell:
            target_path = _resolve_shell_import(import_str, shell_path_set)
        elif is_js_ts:
            ...  # existing
        else:
            target_path = _resolve_import(import_str, module_map)
    ```
  - Build `shell_path_set: frozenset[str] = frozenset(p for p in path_to_id)` once before the loop. Reuse the full `path_to_id` set; do not filter by language. A Python file path that happens to match a shell `source` literal is a real intra-project edge — the cross-language case is rare but legitimate (e.g., a bash script sources a `.env`-style file co-located with a Python service) and the graph builder should not silently drop it.
- No changes required in `src/sdi/parsing/shell.py`. The adapter already produces the shape the new resolver consumes.
- No changes required in `_resolve_import` (the Python module-key resolver) — its behaviour for non-Python files is unchanged.
- Self-import handling, deduplication, and weighted-edge aggregation are shared with the existing branches at `builder.py:430-449`. Do not duplicate that logic in the shell branch.
- Determinism guard — add an explicit comment at the top of `_resolve_shell_import` noting that `_SHELL_EXTENSIONS_FOR_FALLBACK` is intentionally a `tuple` (not a `set`) and that callers must rely on the order. Reviewers commonly "fix" this to a set; the comment exists to deflect that.

**Acceptance criteria:**
- `sdi snapshot` on `tests/fixtures/simple-shell/` (M13 fixture) reports `graph_metrics.edge_count >= 1` (the existing `source ./lib/util.sh` edge resolves).
- `sdi snapshot` on `tests/fixtures/shell-heavy/` (M14 fixture, ≥ 2 cross-script `source` imports) reports `graph_metrics.edge_count >= 2` and `graph_metrics.component_count <= file_count - 1`.
- A new fixture `tests/fixtures/shell-graph/` (8 scripts, ≥ 12 explicit `source` edges spanning relative and `lib/`-style includes) reports `graph_metrics.edge_count >= 12` and `graph_metrics.component_count <= 4`.
- Implicit-extension test: a script with `source ./common` (no extension) resolves to `common.sh` if that file exists; with both `common.sh` and `common.bash` present, resolution prefers `common.sh`.
- Determinism: parsing and building the graph twice on the same fixture inputs produces byte-identical `graph_metrics` dicts and byte-identical `partition_data.inter_cluster_edges` lists.
- **No regression on non-shell languages.** Run the pre-M15 suite, capture `graph_metrics` for every fixture-based snapshot test (Python/TS/JS/Go/Java/Rust). Post-M15, every value in those captured `graph_metrics` dicts must be byte-identical except where the fixture itself contains shell files.
- `unresolved_count` for shell records correctly reflects unresolved `source` literals (e.g., a literal pointing at a path outside `path_to_id` increments `unresolved_count` by exactly 1).

**Tests:** (gate every shell-touching test with `requires_shell_adapter` from `tests/conftest.py`, established in M13)

- `tests/unit/test_graph_builder.py` — extend with:
  - shell record whose `imports = ["lib/util.sh"]` and `path_to_id` contains `"lib/util.sh"` produces exactly one edge `(record_idx → util_idx)`.
  - shell record whose `imports = ["lib/missing.sh"]` produces zero edges and `metadata["unresolved_count"] == 1`.
  - shell record whose `imports = ["common"]` resolves to `common.sh` when only `common.sh` is in the path set.
  - shell record whose `imports = ["common"]` resolves to `common.sh` (not `common.bash`) when both are in the path set — assert the chosen target explicitly, do not just check non-`None`.
  - shell record whose `imports = ["common.sh"]` resolves to `common.sh` directly without extension fallback (literal-match takes precedence).
  - shell record self-loop: `imports = [its own file_path]` increments `metadata["self_import_count"]` by 1, produces no edge.
  - mixed-language input: a single `build_dependency_graph` call with one Python record + one shell record + one TS record each producing one edge via their respective resolvers — verify the graph has exactly 3 edges with the expected `(src, tgt)` pairs.
  - cross-language `source`: a shell record `imports = ["scripts/env.py"]` with `scripts/env.py` in the path set produces an edge (the cross-language case is supported, not silently dropped).
  - extension-fallback negative case: shell record whose `imports = ["common.zsh"]` does **not** resolve via fallback to `common.sh` (the literal already has a known shell extension; fallback is skipped).
  - determinism: build the graph twice on the same record list, assert `g.get_edgelist()` is identical and `vs["name"]` ordering is identical.
- New fixture `tests/fixtures/shell-graph/` containing:
  - 8 scripts: `entrypoint.sh`, `lib/common.sh`, `lib/util.sh`, `lib/log.sh`, `lib/db.sh`, `cmd/deploy.sh`, `cmd/rollback.sh`, `cmd/status.sh`.
  - `entrypoint.sh` sources `lib/common.sh` and `cmd/deploy.sh`, `cmd/rollback.sh`, `cmd/status.sh`.
  - Each `cmd/*.sh` sources `lib/common.sh` and `lib/log.sh`; `cmd/deploy.sh` and `cmd/rollback.sh` additionally source `lib/db.sh`.
  - `lib/common.sh` sources `lib/log.sh`.
  - At least one script uses `source ./common` (no extension) targeting `lib/common.sh` to exercise the fallback.
  - Total: 12 explicit `source` edges (count manually in the fixture README; assert in the test).
- `tests/integration/test_full_pipeline.py` — extend the shell-adapter-gated class with one assertion per acceptance criterion: `edge_count >= 12` and `component_count <= 4` on `shell-graph/`.
- Reference snapshot: before M15 lands, capture `graph_metrics` JSON for every existing fixture test and store under `tests/fixtures/_reference/graph_metrics_pre_m15/`. M15's regression test reads those references and asserts byte equality against post-M15 output. Delete the reference directory at the end of the milestone (it is throwaway scaffolding, not a permanent fixture).

**Watch For:**
- **The shell adapter already resolves paths.** Do not re-resolve in the graph builder. The import string is already a repo-relative POSIX path or already-failed dynamic form; the graph builder's job is direct lookup plus bounded extension fallback only.
- **Extension fallback is bounded by the allow-list.** `.sh` and `.bash` only, in that order. Reviewers commonly suggest expanding to all six shell extensions or using iteration over `frozenset({...})`. Both expansions inflate phantom-edge risk and break determinism — reject them. The allow-list is a tuple, deliberately.
- **No content-dependent fallback.** Do not read file contents from the filesystem during graph resolution. Discovery already established language at parse time; the graph builder operates only on `path_to_id`.
- **Cross-language `source` is legitimate.** A bash script sourcing a `.env`-style co-located file that happens to be a Python file in the path set should produce an edge. Do not filter `shell_path_set` by language — use the full set.
- **Self-imports are still skipped.** Honor the existing `tgt_id == src_id` skip and increment of `self_import_count` (`builder.py:430`). The shell branch shares this behaviour.
- **Function-call edges are out of scope.** Edges in v0/v1 represent *file inclusion*, not function-call relationships. A future milestone may introduce a separate edge kind for cross-file function references — that work is **not** part of M15. Reviewers may suggest adding it; defer to a future milestone with explicit scope.
- **Empty `imports`.** A shell record with `imports == []` (the common case for leaf scripts) must not produce any spurious lookups. Verify in tests.
- **Determinism is bit-stable.** The unit test that builds the graph twice must compare `g.get_edgelist()` exactly, not just `len()`. If the test passes on length alone, the determinism rule is not actually verified.
- **Weighted edges path.** When `config.boundaries.weighted_edges = true`, the shell branch participates in `edge_weight_map` aggregation identically to the other branches. Add one weighted-edges unit case asserting the weight count for a duplicated `source` literal in the same file equals the duplicate count.

**Seeds Forward:**
- Restores `coupling_topology` and `boundary_violations` as meaningful signals on shell-heavy codebases — Leiden cannot return useful clusters when `edge_count == 0`.
- Provides realistic input for M16's per-language pattern catalog scoping. Without edges, M16's per-language signals would still be technically computable but would never exercise the cross-cluster boundary-spread logic.
- Establishes the third dispatch arm pattern, which future adapter milestones (Ruby `require_relative`, Lua `require`, etc.) can reuse if those adapters likewise pre-resolve imports to repo-relative paths.

---

---

## Archived: 2026-04-26 — Unknown Initiative

### Milestone 16: Per-Language Pattern Catalog Scoping and Signals
<!-- milestone-meta
id: "16"
status: "done"
-->


**Scope:** Make the pattern catalog and divergence signals meaningful on mixed-language codebases by attaching applicable-languages metadata to every category and surfacing per-language entropy and convention drift alongside the existing language-agnostic aggregate. Today, `_catalog_pattern_entropy` and `_catalog_convention_drift` (`src/sdi/snapshot/delta.py:29-67`) sum across all categories and all languages; on a 95%-shell repo with 28 Python files, the same `error_handling` category aggregates a Python `try/except` shape and a shell `set -e` shape into one number, and three Python-only categories (`class_hierarchy`, `context_managers`, `comprehensions`) appear in the report with `entropy=0`. Per-language signals make drift interpretable in the dimension that actually changed.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 4, SDI never classifies code as good or bad. This milestone adds *scoping* metadata, not *quality* metadata — a category being "applicable to language X" is a structural property (the AST construct exists in X), not a value judgment. Phrases like "language-appropriate," "irrelevant," "doesn't apply," or "unsupported" are fine; "improper," "wrong-language," or "polluted" are not. Per Rule 12, config keys are never repurposed: `pattern_entropy` and `convention_drift` keep their existing semantics. New per-language fields are *additive* — they do not replace the aggregate.

**Deliverables:**
- `src/sdi/patterns/categories.py`:
  - Add a `languages: frozenset[str]` field to `CategoryDefinition` (`categories.py:25-38`). Default to an empty frozenset; categories with an empty `languages` set are treated as "applies to all languages" for back-compat.
  - Populate `languages` for each built-in category in `_build_registry()` (`categories.py:94-107`):
    - `error_handling`: `frozenset({"python", "shell", "javascript", "typescript", "go", "java", "rust"})` (every supported language has try/except, set -e, panic/recover, throw, Result, etc.)
    - `data_access`: `frozenset({"python", "shell", "javascript", "typescript", "go", "java", "rust"})` (call-site allow-lists exist for every language; absence of a query string for a language means zero detection but the category remains applicable in principle).
    - `logging`: same set as `data_access`.
    - `async_patterns`: `frozenset({"python", "shell", "javascript", "typescript", "go", "rust"})` (Java omitted — `tree-sitter-java` async detection is out of scope for v0; CompletableFuture and friends are not in the catalog).
    - `class_hierarchy`: `frozenset({"python", "javascript", "typescript", "java"})` — Go (no inheritance, just embedding), Rust (traits, not classes), and shell (no classes) are excluded.
    - `context_managers`: `frozenset({"python"})` — Python `with` only. JavaScript `using` (TC39 stage 3 at the time of writing) is not yet detected by SDI's queries; if a future milestone adds a TS/JS query, expand this set in that milestone.
    - `comprehensions`: `frozenset({"python"})` — Python list/dict/set/generator comprehensions only. JavaScript array methods (`.map`, `.filter`) are not comprehensions and are out of scope.
  - Document the rule in a module docstring update: "An empty `languages` set means the category applies to every parsed language. A non-empty set restricts catalog rollups for that category to those languages — files in non-applicable languages cannot contribute instances even if a future adapter mistakenly emits them."
  - Add `def applicable_languages(category: str) -> frozenset[str] | None` returning `None` for unknown categories (consistent with `get_category` returning `None`).
- `src/sdi/patterns/catalog.py`:
  - In `build_pattern_catalog` (`catalog.py:154-216`), filter pattern-instance contributions by category language scope:
    - Resolve each record's language once.
    - For each fingerprint emitted by `get_file_fingerprints`, check `category_def.languages`. If the set is non-empty and `record.language` is not in it, drop the fingerprint silently (it is a programming error in the adapter, not user-facing). Continue otherwise.
  - Add a `category_languages: dict[str, list[str]]` field to `PatternCatalog.to_dict()` mirroring `categories.py` registration. Sort each list for deterministic output.
- New per-language rollup helpers in `src/sdi/snapshot/delta.py`:
  - `_per_language_pattern_entropy(catalog_dict, language_breakdown) -> dict[str, float]` returning `{ language: distinct_shape_count_for_categories_applicable_to_language }`. The denominator is "categories scoped to this language," not "categories present in catalog."
  - `_per_language_convention_drift(catalog_dict, records_or_lang_index) -> dict[str, float]` — same shape as `_catalog_convention_drift` but partitioned. Implementation note: `ShapeStats.file_paths` already lists the files that contribute to a shape; cross-reference each file with its language to attribute instances. Falling back to `language_breakdown` alone is insufficient because a single category mixes files from multiple languages.
  - The existing `_catalog_pattern_entropy` and `_catalog_convention_drift` keep their behaviour unchanged. Both rollups apply the new language scoping at the category level: Python-only categories with no Python files contribute zero (they already do); shell-only categories with only Python files contribute zero. The aggregate becomes "sum across (category, language) pairs where language is in `category.languages`."
- `DivergenceSummary` (`src/sdi/snapshot/model.py:60-93`):
  - Add four new optional fields, mirroring the existing aggregates:
    - `pattern_entropy_by_language: dict[str, float] | None = None`
    - `pattern_entropy_by_language_delta: dict[str, float] | None = None`
    - `convention_drift_by_language: dict[str, float] | None = None`
    - `convention_drift_by_language_delta: dict[str, float] | None = None`
  - Update `to_dict` and `from_dict` to round-trip these fields. `from_dict` must default missing keys to `None` so older snapshots still deserialize (Non-Negotiable Rule 13).
  - Bump `SNAPSHOT_VERSION` from `"0.1.0"` to `"0.2.0"` in `src/sdi/snapshot/model.py:14`. The schema gained additive fields, so per Rule 13 trend computation against a `"0.1.0"` snapshot must warn and treat it as a baseline (no delta), not crash. Update `delta.py:_major_version` callers if needed — major version is unchanged (`0`), so existing major-version compatibility branch still applies.
- `compute_delta` (`src/sdi/snapshot/delta.py:127-196`):
  - Compute the four new per-language fields for `current`. When `previous is None`, all `_delta` fields are `None`.
  - When `previous` is present and same major version, compute deltas as `dict` differences keyed on language: any language present in either current or previous appears in the delta dict with a numeric value (defaulting to `0.0` when absent on one side). When `previous` is present but lacks the per-language fields (older `"0.1.0"` snapshot), treat as if `previous` were absent for the per-language deltas only — emit a `UserWarning` once and proceed.
- `sdi show` and `sdi diff` output (`src/sdi/cli/show_cmd.py`, `src/sdi/cli/diff_cmd.py`):
  - In text mode, render a per-language section after the existing aggregate when `pattern_entropy_by_language` is not `None`. One row per language sorted by file count (descending), with absolute and delta columns. No color thresholds; this is measurement output.
  - In `--format json` mode, the new fields appear in the output dict alongside the existing aggregate. No transformation.
- Documentation:
  - Extend `README.md`'s "what SDI measures" section with a one-paragraph note: "Pattern entropy and convention drift are reported globally and per-language. Categories declare which languages they apply to; non-applicable languages contribute zero. A 95%-shell repo's `error_handling` entropy under `pattern_entropy_by_language["shell"]` reflects shell-specific shapes only."
  - Add a `CHANGELOG.md` entry under "Unreleased": `Added: per-language pattern entropy and convention drift fields in DivergenceSummary; CategoryDefinition gains an applicable-languages field. Snapshot schema bumped to 0.2.0 (additive only).`

**Acceptance criteria:**
- Every built-in category has a non-empty `languages` field. Calling `applicable_languages(name)` for any name in `CATEGORY_NAMES` returns a non-empty `frozenset[str]`; for unknown names returns `None`.
- A snapshot of `tests/fixtures/multi-language/` (Python + TypeScript) reports `pattern_entropy_by_language` with at least two keys (`"python"` and `"typescript"`), each with non-zero entropy, and an aggregate `pattern_entropy` equal to the sum of distinct shapes across all (category, language) pairs where the language is applicable.
- A snapshot of `tests/fixtures/shell-heavy/` (M14 fixture) reports `pattern_entropy_by_language["shell"] > 0` and `pattern_entropy_by_language` has no `"python"` key (the fixture has zero Python files).
- A snapshot of a Python-only fixture reports `pattern_entropy_by_language["python"] > 0` and includes contributions from `class_hierarchy`, `context_managers`, `comprehensions` (Python-only categories) only under the `"python"` key.
- `convention_drift_by_language` partitions correctly: a Python file with a non-canonical `error_handling` shape and a shell file with a non-canonical `error_handling` shape produce two separate per-language drift values, each computed against its own canonical-per-category-per-language baseline.
- `compute_delta` against a `"0.1.0"` snapshot emits exactly one `UserWarning` per snapshot pair and returns `pattern_entropy_by_language_delta is None`. The aggregate `pattern_entropy_delta` is still computed normally.
- Snapshot round-trip: `Snapshot.from_dict(s.to_dict())` yields a `Snapshot` equal to `s` for both new and old (`"0.1.0"`) JSON inputs.
- **Determinism unchanged:** running `sdi snapshot` twice on the same fixture produces byte-identical JSON output, including the new per-language fields. Verify by hashing the serialized output in a unit test.
- **No regression on aggregate values.** For every existing fixture, the aggregate `pattern_entropy` value post-M16 must equal pre-M16 (since every category's `languages` set covers all languages that actually contribute instances on those fixtures). Capture pre-M16 aggregates in a reference snapshot and assert equality.
- `class_hierarchy`, `context_managers`, and `comprehensions` no longer contribute to non-Python languages: a fixture with a fabricated shell adapter that emits a `class_hierarchy` instance for a shell file (test-only adapter) has the instance silently dropped at catalog build time, and `pattern_entropy_by_language["shell"]` excludes it.

**Tests:**

- `tests/unit/test_categories.py` — extend (or create if absent) with:
  - one case per built-in category asserting `applicable_languages(name)` returns the expected frozenset.
  - `applicable_languages("does_not_exist")` returns `None`.
  - empty `languages` field is treated as "applies to all" — fabricate a `CategoryDefinition` with `languages=frozenset()`, register it through a private hook, verify catalog rollups include it for any language.
- `tests/unit/test_catalog.py` — extend with:
  - `build_pattern_catalog` filters out fingerprints whose category does not apply to the record's language. Use a stub fingerprint generator that emits `class_hierarchy` for a shell record; assert the resulting catalog has zero `class_hierarchy` instances.
  - `category_languages` round-trips through `to_dict` / `from_dict` with sorted lists.
- `tests/unit/test_delta.py` — extend with:
  - per-language entropy on a Python+Shell catalog: assert two keys, each with the expected count.
  - per-language drift on a Python+Shell catalog: assert two keys, each with the expected fraction.
  - delta against `previous=None`: all per-language `_delta` fields are `None`.
  - delta against a synthetic previous snapshot lacking per-language fields: emits exactly one `UserWarning`, returns per-language `_delta` as `None` while the aggregate `_delta` is computed.
  - delta with new languages added: a previous snapshot with only `python`, current with `python` + `shell`, returns a delta dict containing both keys with `previous` shell value treated as `0.0`.
- `tests/unit/test_snapshot_model.py` — extend with:
  - `DivergenceSummary` round-trips through `to_dict` / `from_dict` with all four new fields populated.
  - `Snapshot.from_dict` accepts JSON missing the new fields (a `"0.1.0"` snapshot) and produces a `Snapshot` with `pattern_entropy_by_language=None` etc.
- `tests/integration/test_full_pipeline.py` — extend the `multi-language` and `shell-heavy` cases with per-language assertions matching the acceptance criteria above.
- `tests/integration/test_cli_output.py` — assert `sdi show --format json` for a multi-language snapshot includes the per-language keys, and the text-mode output renders the per-language section.

**Watch For:**
- **Empty `languages` means "applies to all," not "applies to none."** This is a deliberate back-compat default for any future externally-defined category. Reviewers may flip the semantic to "empty means none" — that breaks the back-compat path and should be rejected. Make the convention explicit in the `CategoryDefinition` docstring.
- **`class_hierarchy`, `context_managers`, `comprehensions` are Python-only intentionally.** TS/JS classes do exist syntactically but the existing query strings target Python AST node names (`class_definition`, `with_statement`, `list_comprehension`). If a future milestone adds TS/JS queries, expand the `languages` set in *that* milestone — do not pre-emptively expand here.
- **Aggregate semantics must not change for existing inputs.** The aggregate `pattern_entropy` for a Python-only fixture must equal its pre-M16 value. The category-language scoping only excludes hypothetical fingerprints that adapters never actually emit today — it should be a no-op on existing fixture suites. The regression assertion in acceptance criteria enforces this.
- **`SNAPSHOT_VERSION` bump is additive-only.** `0.1.0` → `0.2.0` is a minor bump because the schema gained optional fields. Major version `0` is unchanged, so the existing `_major_version` compatibility branch in `delta.py` continues to allow trend computation across the bump. If `from_dict` needs to handle missing keys, do it via `.get(key)` with `None` default, never via raising.
- **Determinism: per-language dicts must be deterministically ordered when serialized.** Use sorted keys explicitly when producing `dict[str, float]` outputs so JSON round-trip is byte-stable. `json.dumps(..., sort_keys=True)` is the standard guard.
- **`async_patterns` mixing across languages is intentional and inherited from M14.** Per-language scoping does not split `async_patterns` into per-language sub-categories. A Python `async def` shape and a shell `command &` shape are different shapes (different ast_hashes) within the same category — the per-language rollup partitions *files*, not categories. Reviewers may flag the cross-language presence as a smell; it remains intentional.
- **Drift computation requires per-language canonicals.** `_catalog_convention_drift` picks one canonical hash per category. The per-language version must pick one canonical hash per (category, language) pair — otherwise a Python file is graded against a shell canonical or vice versa. This is the most common implementation mistake; add a unit case that fails if the canonical is not partitioned.
- **`languages` field is metadata, not enforcement.** The catalog filter is defensive only. The primary correctness mechanism is each adapter emitting category names that match its language's queries. The filter exists to make accidents in adapter code visible by silent zeroing, not to substitute for adapter discipline.
- **No new config key.** Per-language behaviour is unconditional — there is no `[patterns] per_language = true` flag. The aggregate still exists for back-compat consumers, and the per-language fields are always present on new snapshots. Adding a flag would create three behaviours (off / aggregate / per-language) and complicate diffing.

**Seeds Forward:**
- Makes `sdi check` thresholds amenable to per-language overrides in a future milestone (e.g., `[thresholds.overrides.error_handling.shell]`). M16 does not implement per-language thresholds — it provides the signal those thresholds would key off.
- Lays groundwork for per-language trend visualization (a future `sdi trend --by-language` flag).
- Reduces the noise in mixed-language snapshots that the validation harness in M18 must assert against.

---
