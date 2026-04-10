### Milestone 2: Source Parsing and File Discovery

**Scope:** Implement Stage 1 of the pipeline: file discovery (respecting `.gitignore` and exclude patterns), language detection, tree-sitter parsing, and per-file feature extraction. This milestone delivers the parsing infrastructure and the Python language adapter. Other language adapters are deferred to Milestone 7. The feature record data structure established here is the input contract for Stages 2–4.

**Deliverables:**
- File discovery module that walks the repo tree, respects `.gitignore` and config exclude patterns, and detects languages by file extension
- Base language adapter interface defining the contract for language-specific parsers
- Python language adapter using tree-sitter-python: extracts imports, function/class definitions, exported symbols, and pattern-relevant AST subtrees
- Parallel parsing orchestrator using `concurrent.futures.ProcessPoolExecutor`
- `FeatureRecord` dataclass: per-file output containing symbols, imports, and pattern instances
- Parse cache: content-addressed (SHA-256 of file bytes), stores extracted features, skips unchanged files

**Files to create or modify:**
- `src/sdi/parsing/__init__.py`
- `src/sdi/parsing/discovery.py`
- `src/sdi/parsing/base.py`
- `src/sdi/parsing/python.py`
- `tests/unit/test_discovery.py`
- `tests/unit/test_python_parser.py`
- `tests/fixtures/simple-python/` (create fixture project)

**Acceptance criteria:**
- `discovery.discover_files(repo_root, config)` returns a list of `(path, language)` tuples, excluding `.gitignore`'d paths and config exclude patterns
- Language detection correctly identifies `.py` files as Python
- Files with no matching grammar are silently skipped (not errors)
- Python adapter extracts: import statements (module + imported names), function definitions (name, decorators), class definitions (name, bases), try/except blocks with their structure
- `FeatureRecord` contains: `file_path`, `language`, `imports`, `symbols`, `pattern_instances`
- Parse cache stores results keyed by file content SHA-256; second parse of unchanged file hits cache
- Parsing runs in parallel with worker count respecting `SDI_WORKERS` env var
- Full CSTs are not held in memory simultaneously — parse, extract, discard per file
- `tests/fixtures/simple-python/` contains a small project with known imports, classes, and pattern instances

**Tests:**
- `tests/unit/test_discovery.py`:
  - Files in `.gitignore` are excluded
  - Config exclude patterns are applied
  - Non-source files (images, binaries) are skipped
  - Nested directories are walked
  - Symlinks are handled (followed or skipped per platform)
- `tests/unit/test_python_parser.py`:
  - Import extraction: `import foo`, `from foo import bar`, `from foo import bar, baz`
  - Class extraction: name, base classes
  - Function extraction: name, decorators
  - Try/except block detection: simple try/except, try/except/finally, nested try blocks
  - Empty file produces empty feature record (not an error)
  - Syntax errors in source files produce a warning, not a crash

**Watch For:**
- tree-sitter Python bindings v0.24+ changed the API significantly. Ensure you use the current API: `tree_sitter.Language` from `tree_sitter_python` directly, not the old `Language.build_library()` approach.
- `.gitignore` parsing is non-trivial (negation patterns, directory-only patterns). Consider using `pathspec` library for gitignore-compatible matching rather than reimplementing.
- `ProcessPoolExecutor` requires that all data passed to workers is picklable. The tree-sitter `Parser` object is NOT picklable — each worker must create its own parser instance.
- Parse cache files should be written atomically (same tempfile + rename pattern as snapshots).

**Seeds Forward:**
- `FeatureRecord` is the input contract for graph construction (Milestone 3) and pattern fingerprinting (Milestone 5). Its shape must be stable.
- The base adapter interface (`src/sdi/parsing/base.py`) defines the contract that all language adapters in Milestone 7 implement.
- Pattern-relevant AST subtrees stored in `FeatureRecord.pattern_instances` must carry enough structural information for fingerprinting in Milestone 5 — include node types and tree structure, not just counts.
- The parallel parsing orchestrator is reused directly in the full pipeline (Milestone 6).

---
