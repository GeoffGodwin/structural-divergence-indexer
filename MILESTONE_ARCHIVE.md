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
