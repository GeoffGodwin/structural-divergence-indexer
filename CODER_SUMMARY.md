# Coder Summary
## Status: COMPLETE

## What Was Implemented

- **`src/sdi/parsing/_js_ts_common.py`** (NEW): Shared utilities for TypeScript and
  JavaScript adapters — `extract_es_imports`, `extract_require_imports`,
  `extract_reexport_imports`, `extract_symbols`, `extract_pattern_instances`,
  `count_loc`, `_structural_hash`, `_location`, `_walk_nodes`, `string_fragment`,
  `node_text`, `_is_require_call`.

- **`src/sdi/parsing/typescript.py`** (NEW): TypeScript adapter. Handles `.ts`/`.tsx`
  files. Extracts ES imports, type-only imports (annotated with `type:` prefix in
  `FeatureRecord.imports`), CommonJS `require()`, and re-exports. Detects
  `error_handling` and `logging` pattern instances.

- **`src/sdi/parsing/javascript.py`** (NEW): JavaScript adapter. Handles `.js`/`.mjs`/
  `.cjs` files. Extracts ES imports, CommonJS `require()`, dynamic `import()`, and
  re-exports. Detects `error_handling` and `logging` pattern instances.

- **`src/sdi/parsing/go.py`** (NEW): Go adapter. Handles `.go` files. Extracts import
  package paths (slash-separated, stored as-is). Detects exported symbols
  (capitalized names only). Detects `error_handling` pattern instances (`if err != nil`).

- **`src/sdi/parsing/java.py`** (NEW): Java adapter. Handles `.java` files. Extracts
  qualified import paths including wildcard imports (`java.util.*`). Extracts class
  and interface names as symbols. Detects `error_handling` (try/catch) patterns.

- **`src/sdi/parsing/rust.py`** (NEW): Rust adapter. Handles `.rs` files. Extracts
  `use` declarations (`::`-separated paths) and external `mod` declarations (stored
  as `./foo` relative path references — see Seeds Forward convention). Extracts
  `pub` items as symbols. Detects `error_handling` patterns (match on Result/Option).

- **`src/sdi/parsing/_runner.py`** (MODIFIED): Registered all five new adapters via
  `importlib.import_module` in the `_register_adapters()` function. Each adapter
  handles its own `ImportError` gracefully (grammar not installed → warning, not error).

- **`tests/fixtures/multi-language/`** (NEW directory): 7 files:
  - `models.py`, `service.py`, `utils.py` — Python files with known imports and patterns
  - `api.ts`, `client.ts`, `models.ts`, `types.ts` — TypeScript files with known
    imports (including type-only), symbols, and pattern instances.

- **`tests/unit/test_typescript_adapter.py`** (NEW): 30 tests covering ES imports,
  type-only imports, CommonJS require, re-exports, symbols, patterns, metadata.

- **`tests/unit/test_javascript_adapter.py`** (NEW): 24 tests covering ES imports,
  CommonJS require, dynamic imports, symbols, patterns, metadata.

- **`tests/unit/test_go_adapter.py`** (NEW): 23 tests covering single/grouped/aliased
  imports, exported symbol detection, error_handling patterns, metadata.

- **`tests/unit/test_java_adapter.py`** (NEW): 24 tests covering import statements,
  wildcard imports, package declarations, class/interface definitions, patterns, metadata.

- **`tests/unit/test_rust_adapter.py`** (NEW): 26 tests covering use statements,
  mod declarations (external vs inline), pub items, trait/impl blocks, patterns, metadata.

## Architecture Change Proposals

**Type-only import annotation convention (`type:` prefix)**
- **Current constraint**: `FeatureRecord.imports` is `list[str]` with no field for
  type-annotation metadata.
- **What triggered this**: Acceptance criteria requires TypeScript adapter to
  distinguish type-only imports from value imports; both must create graph edges but
  type-only ones must be annotated.
- **Proposed change**: Type-only imports stored as `type:<module-path>` in the
  `imports` list (e.g., `type:./types`). The graph builder (M4) must strip this
  prefix when building edges and may use it to tag edges as "type-only".
- **Backward compatible**: Yes — existing Python imports are unaffected. New prefix
  is additive and opt-in per language.
- **ARCHITECTURE.md update needed**: No. Document this convention in the M4 graph
  builder when it is implemented.

**External mod declaration as relative import (`./foo`)**
- **Current constraint**: `FeatureRecord.imports` was conceived for explicit import
  paths. Rust `mod foo;` creates an implicit file dependency.
- **What triggered this**: Seeds Forward note in M03 mandates handling of Rust
  `mod` declarations. Must be normalized before reaching the graph builder.
- **Proposed change**: External `mod foo;` is stored as `./foo` in `imports`. Inline
  `mod foo { ... }` (has a body) is ignored — no file dependency. The `./` prefix
  distinguishes file-relative references from package paths.
- **Backward compatible**: Yes — no existing code produces `./`-prefixed imports.
- **ARCHITECTURE.md update needed**: No. Document in M4 graph builder.

## Files Modified

| File | Status |
|------|--------|
| `src/sdi/parsing/_js_ts_common.py` | NEW |
| `src/sdi/parsing/typescript.py` | NEW |
| `src/sdi/parsing/javascript.py` | NEW |
| `src/sdi/parsing/go.py` | NEW |
| `src/sdi/parsing/java.py` | NEW |
| `src/sdi/parsing/rust.py` | NEW |
| `src/sdi/parsing/_runner.py` | MODIFIED |
| `tests/fixtures/multi-language/models.py` | NEW |
| `tests/fixtures/multi-language/service.py` | NEW |
| `tests/fixtures/multi-language/utils.py` | NEW |
| `tests/fixtures/multi-language/api.ts` | NEW |
| `tests/fixtures/multi-language/client.ts` | NEW |
| `tests/fixtures/multi-language/models.ts` | NEW |
| `tests/fixtures/multi-language/types.ts` | NEW |
| `tests/unit/test_typescript_adapter.py` | NEW |
| `tests/unit/test_javascript_adapter.py` | NEW |
| `tests/unit/test_go_adapter.py` | NEW |
| `tests/unit/test_java_adapter.py` | NEW |
| `tests/unit/test_rust_adapter.py` | NEW |

## Human Notes Status
No human notes listed in task.

## Observed Issues (out of scope)
- `src/sdi/parsing/_python_patterns.py:138`: `in_multiline_string` variable
  declared but never used (vestigial from an earlier draft). Not fixed — out of scope.
