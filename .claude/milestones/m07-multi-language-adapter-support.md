### Milestone 7: Multi-Language Adapter Support

**Scope:** Implement tree-sitter language adapters for TypeScript, JavaScript, Go, Java, and Rust. Normalize cross-language dependency semantics into the language-agnostic graph. Add language-specific tree-sitter queries for each built-in pattern category. Create the multi-language test fixture.

**Deliverables:**
- TypeScript adapter: import/export extraction, class/function/interface definitions, pattern queries
- JavaScript adapter: import/require extraction, function/class definitions, pattern queries
- Go adapter: import extraction, function/struct definitions, pattern queries
- Java adapter: import extraction, class/method definitions, pattern queries
- Rust adapter: use extraction, function/struct/impl definitions, pattern queries
- Cross-language import normalization: all adapters produce the same edge type in the dependency graph
- Language-specific pattern queries for each of the 7 built-in categories across all 6 languages
- Multi-language test fixture
- Auto-detection of languages from file extensions (`.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.java`, `.rs`)

**Files to create or modify:**
- `src/sdi/parsing/typescript.py`
- `src/sdi/parsing/javascript.py`
- `src/sdi/parsing/go.py`
- `src/sdi/parsing/java.py`
- `src/sdi/parsing/rust.py`
- `src/sdi/patterns/categories.py` (extend with per-language queries)
- `tests/unit/test_typescript_parser.py`
- `tests/unit/test_javascript_parser.py`
- `tests/unit/test_go_parser.py`
- `tests/unit/test_java_parser.py`
- `tests/unit/test_rust_parser.py`
- `tests/fixtures/multi-language/` (create fixture)

**Acceptance criteria:**
- Each adapter extracts imports, symbol definitions, and pattern-relevant AST subtrees for its language
- TypeScript: `import { Foo } from './bar'`, `import * as X from 'mod'`, `export class`, `interface`
- JavaScript: `const X = require('./bar')`, `import X from './bar'`, `module.exports`
- Go: `import "fmt"`, `import ("fmt"; "os")`, `func`, `type Foo struct`
- Java: `import com.example.Foo`, `class`, `interface`, `@Override`
- Rust: `use std::io`, `use crate::module`, `fn`, `struct`, `impl`
- All adapters produce `FeatureRecord` objects compatible with graph builder
- Missing grammar for a language produces a warning with install hint: `pip install tree-sitter-kotlin`
- `sdi snapshot` on multi-language fixture produces a unified dependency graph
- Pattern queries detect language-appropriate patterns (e.g., Go error handling via `if err != nil`, Rust via `match Result`, Python via `try/except`)
- Fingerprints are comparable across languages: structurally equivalent error handling in Python and TypeScript may or may not produce the same fingerprint, but the category grouping is correct

**Tests:**
- One test file per adapter with cases for:
  - Import extraction (all import styles for that language)
  - Symbol definition extraction (functions, classes, interfaces, structs)
  - At least one pattern category query (error handling recommended as it varies most)
  - Empty file handling
  - Syntax error handling (warning, not crash)
- `tests/fixtures/multi-language/`: Python + TypeScript project with a known dependency between a Python module and a TypeScript module (no cross-language edge expected in v1, but both appear in the same graph)

**Watch For:**
- Tree-sitter grammar packages have different API conventions. TypeScript uses `tree_sitter_typescript.language_typescript()` and `tree_sitter_typescript.language_tsx()` for `.ts` and `.tsx` respectively.
- JavaScript and TypeScript share much structure but have different grammars. Do NOT reuse the TypeScript adapter for JavaScript — they have different tree-sitter grammars and different import semantics (`require` vs `import`).
- Go's import resolution uses module paths, not filesystem paths. SDI resolves local imports (same module) but treats external module imports the same as Python's external imports — recorded but no graph edge.
- Java's package-to-path mapping relies on directory structure conventions. Use filesystem-based resolution, not classpath resolution.
- Rust's `use` statements can be deeply nested (`use std::collections::HashMap`). Extract the top-level crate/module name for import resolution.
- Pattern queries must be tested against REAL code snippets, not synthetic examples. Use actual common patterns from each ecosystem.

**Seeds Forward:**
- With all six languages supported, the full `[all]`, `[web]`, `[systems]` extras in `pyproject.toml` become functional.
- Multi-language support enables the realistic benchmarks needed in Milestone 10.
- The cross-language fixture establishes the baseline for future cross-language dependency detection (post-v1).

---
