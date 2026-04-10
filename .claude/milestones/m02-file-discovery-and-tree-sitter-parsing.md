### Milestone 2: File Discovery and Tree-Sitter Parsing

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
