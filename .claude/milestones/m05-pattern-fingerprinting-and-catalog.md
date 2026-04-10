### Milestone 5: Pattern Fingerprinting and Catalog

**Scope:** Implement Stage 4 of the pipeline: pattern fingerprinting, catalog construction, entropy computation, velocity tracking, and boundary spread measurement. Deliver the `sdi catalog` command. This milestone focuses on the Python language patterns; other languages are added in Milestone 7.

**Deliverables:**
- Structural fingerprint computation: normalize AST subtree shapes (node types + structure, stripped of identifiers/literals), hash for O(1) grouping
- Pattern catalog: groups fingerprints by category, identifies canonical shape (most frequent) per category
- Built-in pattern category definitions with tree-sitter queries for Python: `error_handling`, `data_access`, `api_validation`, `logging`, `dependency_injection`, `async_patterns`, `config_access`
- Pattern entropy computation: count of distinct shapes per category
- Per-shape velocity: instance count delta versus previous snapshot (null for first snapshot)
- Per-shape boundary spread: count of distinct boundaries each shape spans (using cluster assignments from Milestone 4)
- Fingerprint cache: content-addressed, keyed by file content hash
- `sdi catalog` command with `--category` filter and `--format text|json`

**Files to create or modify:**
- `src/sdi/patterns/__init__.py`
- `src/sdi/patterns/fingerprint.py`
- `src/sdi/patterns/catalog.py`
- `src/sdi/patterns/categories.py`
- `src/sdi/cli/catalog_cmd.py`
- `tests/unit/test_fingerprint.py`
- `tests/unit/test_catalog.py`
- `tests/fixtures/high-entropy/` (create fixture)

**Acceptance criteria:**
- Structurally equivalent AST subtrees produce identical fingerprints regardless of identifier names
- Structurally different AST subtrees produce different fingerprints
- Pattern category queries detect the documented patterns: try/except blocks (error_handling), database calls (data_access), validation checks (api_validation), log calls (logging), constructor injection (dependency_injection), async/await (async_patterns), config reads (config_access)
- Canonical shape per category is the most frequent shape
- Entropy is correctly computed as the count of distinct shapes per category
- Velocity is null for first snapshot, correct integer delta for subsequent snapshots
- Boundary spread correctly counts how many cluster boundaries each shape appears in
- `min_pattern_nodes` config value is respected (AST subtrees smaller than threshold are ignored)
- Fingerprint cache stores results keyed by file content SHA-256
- `sdi catalog` shows all categories with shape counts
- `sdi catalog --category error_handling` filters to one category
- `sdi catalog --format json` outputs structured JSON
- `tests/fixtures/high-entropy/` has 4+ error handling styles and 3+ data access patterns

**Tests:**
- `tests/unit/test_fingerprint.py`:
  - Two `try: ... except ValueError: ...` blocks with different variable names produce same fingerprint
  - `try/except` vs `try/except/finally` produce different fingerprints
  - Nested `try` blocks produce different fingerprint from flat `try` blocks
  - Fingerprint hashing is deterministic
  - Subtrees below `min_pattern_nodes` threshold are excluded
- `tests/unit/test_catalog.py`:
  - Catalog correctly groups fingerprints by category
  - Canonical shape is the most frequent
  - Entropy equals count of distinct shapes per category
  - Velocity computation: given two catalogs, delta is correct
  - Velocity is null when no previous catalog exists
  - Boundary spread computation with known cluster assignments
  - Category with zero instances reports entropy 0, not an error

**Watch For:**
- Fingerprint normalization must strip ALL identifiers and literals, not just some. A `try: call_a() except: pass` and `try: call_b() except: pass` must produce identical fingerprints because the function names are identifiers.
- Tree-sitter query syntax varies by grammar version. Pin grammar versions and test queries against specific grammar versions.
- The `min_pattern_nodes` threshold must count AST nodes in the subtree, not characters or lines. Use tree-sitter's `descendant_count` or manual traversal.
- Boundary spread requires cluster assignments from Milestone 4. When boundaries are not available (no detection run, graph too small), boundary spread is reported as null, not zero.

**Seeds Forward:**
- `PatternCatalog` is included in the snapshot (Milestone 6). Its serialization format must be stable.
- Per-shape velocity and boundary spread are the "second-order signals" reported in `sdi diff` and `sdi trend` (Milestone 6) for human assessment of drift-vs-evolution.
- Language-specific tree-sitter queries in `categories.py` are the extension point for Milestone 7's language adapters.

---
