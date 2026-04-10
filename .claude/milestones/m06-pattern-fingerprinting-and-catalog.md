### Milestone 6: Pattern Fingerprinting and Catalog

**Scope:** Build Stage 4 of the pipeline — pattern fingerprinting, catalog construction, and entropy computation. Implement the seven built-in pattern categories, structural hashing of AST subtrees, canonical pattern identification, and per-shape velocity / boundary spread computation. This milestone produces the `PatternCatalog` with entropy measurements.

**Deliverables:**
- `src/sdi/patterns/__init__.py` with `build_pattern_catalog(records: list[FeatureRecord], config: SDIConfig, prev_catalog: PatternCatalog | None, partition: CommunityResult | None) -> PatternCatalog` public API
- `src/sdi/patterns/fingerprint.py` with `PatternFingerprint` class: structural hash computation from AST subtree descriptors (normalized — node types and structure, stripped of identifiers and literals), equality and comparison based on hash
- `src/sdi/patterns/catalog.py` with `PatternCatalog` class: groups fingerprints by category, identifies canonical pattern per category (most frequent shape), computes pattern entropy per category (count of distinct shapes), computes per-shape velocity (instance count delta vs. previous catalog), computes per-shape boundary spread (count of distinct boundaries each shape spans)
- `src/sdi/patterns/categories.py` with seven built-in category definitions and their tree-sitter query patterns for Python (other languages added per-adapter)
- `tests/fixtures/high-entropy/` with 10+ Python files containing 4+ error handling styles, 3+ data access patterns, 2+ logging styles
- `tests/unit/test_fingerprint.py`
- `tests/unit/test_catalog.py`

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

**Tests:**
- `tests/unit/test_fingerprint.py`: Identical AST shapes produce same hash, different shapes produce different hashes, identifier stripping works (same structure with different variable names = same hash), literal stripping works, minimum node threshold filters small patterns, empty AST subtree handled gracefully
- `tests/unit/test_catalog.py`: Catalog groups fingerprints by category correctly, entropy counts distinct shapes, canonical is most frequent shape, velocity computation (current minus previous instance counts), velocity is null on first snapshot, boundary spread counts distinct boundaries, empty category has entropy 0, catalog JSON round-trip, high-entropy fixture produces expected entropy values

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
