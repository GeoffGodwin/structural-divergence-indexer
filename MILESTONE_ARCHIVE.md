# Milestone Archive

Completed milestone definitions archived from CLAUDE.md.
See git history for the commit that completed each milestone.

---

## Archived: 2026-04-10 — Unknown Initiative

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

## Archived: 2026-04-10 — Unknown Initiative

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

## Archived: 2026-04-10 — Unknown Initiative

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

## Archived: 2026-04-11 — Unknown Initiative


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
