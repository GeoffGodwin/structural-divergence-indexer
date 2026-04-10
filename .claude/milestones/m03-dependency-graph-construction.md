### Milestone 3: Dependency Graph Construction

**Scope:** Implement Stage 2 of the pipeline: build a directed dependency graph from the feature records produced by Stage 1. Nodes are files, edges are import/dependency relationships. Compute graph metrics (density, connected components, cycle count, hub concentration). This milestone works exclusively with Python import resolution. Cross-language normalization is deferred to Milestone 7.

**Deliverables:**
- Graph builder that takes a list of `FeatureRecord` objects and produces an igraph `Graph`
- Import resolution: maps Python import statements to file paths in the repository
- Graph metrics computation: node count, edge count, density, connected components, cycle count, hub nodes (by in-degree centrality), max dependency depth
- Optional edge weighting by import frequency (symbol count per import)

**Files to create or modify:**
- `src/sdi/graph/__init__.py`
- `src/sdi/graph/builder.py`
- `src/sdi/graph/metrics.py`
- `tests/unit/test_graph_builder.py`
- `tests/unit/test_graph_metrics.py`

**Acceptance criteria:**
- Given `FeatureRecord` objects with known imports, the graph contains the correct directed edges
- Python import `from src.billing.models import Invoice` resolves to the correct file node
- Relative imports (`from . import utils`) resolve correctly
- Unresolvable imports (external packages) are recorded but do not create edges to phantom nodes
- Graph metrics are computed and returned as a dictionary
- Cycle detection identifies all cycles in the graph
- Hub detection returns top-N nodes by in-degree centrality
- `weighted_edges=true` in config produces weighted edges based on imported symbol count
- `weighted_edges=false` (default) produces unweighted edges
- An empty repository (no imports) produces a valid graph with nodes but no edges

**Tests:**
- `tests/unit/test_graph_builder.py`:
  - Simple linear dependency chain: A → B → C produces correct edges
  - Diamond dependency: A → B, A → C, B → D, C → D
  - Circular dependency: A → B → A produces a cycle
  - External imports are excluded from graph edges
  - Relative imports resolve correctly
  - Weighted vs unweighted edge construction
- `tests/unit/test_graph_metrics.py`:
  - Density of a complete graph = 1.0
  - Cycle count on acyclic graph = 0
  - Hub detection returns highest in-degree nodes
  - Connected components count matches expected value
  - Empty graph (no edges) metrics are valid (not errors)

**Watch For:**
- Python import resolution is complex: `__init__.py` packages, namespace packages, relative imports, conditional imports. Start with simple cases (absolute imports, single-level packages) and expand. Do NOT try to replicate Python's full import machinery.
- igraph vertex names must be unique. Use canonical file paths (relative to repo root) as vertex names.
- Cycle detection on large graphs can be expensive. Use igraph's built-in `feedback_arc_set()` or `is_dag()` rather than implementing from scratch.

**Seeds Forward:**
- The `Graph` object is the input to Leiden community detection (Milestone 4). Ensure the igraph graph is returned with vertex attributes that include file path and language.
- Graph metrics are included in the final snapshot (Milestone 6). The metrics dictionary format established here must be stable.
- The builder's import resolution interface must be language-adapter-aware so that Milestone 7 can add TypeScript, Go, etc. import resolution without changing the builder's API. Use a resolver callback or strategy pattern.

---
