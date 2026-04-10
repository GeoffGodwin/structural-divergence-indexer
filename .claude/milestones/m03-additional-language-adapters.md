### Milestone 3: Additional Language Adapters

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
