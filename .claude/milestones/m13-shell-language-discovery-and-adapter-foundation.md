### Milestone 13: Shell Language Discovery and Adapter Foundation
<!-- milestone-meta
id: "13"
status: "planned"
-->


**Scope:** Add first-class shell parsing support to SDI's Stage 1 pipeline so shell scripts are discovered, parsed, and represented as FeatureRecords with deterministic behavior and graceful degradation when grammar dependencies are missing.

**Deliverables:**
- Shell grammar dependency wiring:
  - Add `tree-sitter-bash` (canonical PyPI package, no version pin needed beyond what `tree-sitter>=0.24` constrains) to the `all` optional extra in `pyproject.toml` (alongside the other `tree-sitter-*` packages at `pyproject.toml:42-52`).
  - Add `tree-sitter-bash` to the `[[tool.mypy.overrides]] module = [...]` list at `pyproject.toml:72-74` so missing type stubs do not fail `mypy`.
  - Import failure handling is automatic: `_register_adapters` in `src/sdi/parsing/_runner.py:22-44` already wraps adapter imports in `try/except ImportError` and emits a `[warning]` to stderr. The shell adapter only needs to be appended to the `_adapter_modules` list — no additional warning code required.
- Discovery updates in `src/sdi/parsing/discovery.py`:
  - Extend `_EXTENSION_TO_LANGUAGE` (`discovery.py:10-20`) with: `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash` → `"shell"`. Do **not** map `.fish`; fish syntax is incompatible with `tree-sitter-bash` and parse failures would corrupt downstream analysis. `.fish` files fall into the existing "no grammar" warning path automatically.
  - Add shebang-based detection for extensionless scripts via a private helper `_detect_shell_shebang(path: Path) -> bool` in `discovery.py`. Behaviour:
    - **Trigger:** only for files where `detect_language(path)` returns `None` AND `path.suffix == ""` AND the executable bit is set (`path.stat().st_mode & 0o111 != 0`). Skip otherwise — never read content for files that already have a known/unknown extension.
    - **Read:** open in binary mode and read at most 256 bytes (one `read(256)`). Decode with `errors="replace"`. Inspect only the first line.
    - **Match rule:** the first line must start with `#!` and the remainder must contain a path component (split on `/` and whitespace) equal to one of: `sh`, `bash`, `zsh`, `ksh`, `dash`, `ash`. Reject `python`, `python3`, `node`, `ruby`, `perl`, `awk`, `sed`, etc. For `#!/usr/bin/env <cmd>`, take `<cmd>` (the first whitespace-separated token after `env`) and apply the same allow-list.
    - **Integration:** call `_detect_shell_shebang` inside `discover_files` after the existing `detect_language` check; on True, append `(path, "shell")` to results. Apply gitignore/exclude filters before the shebang check (mirror existing order).
  - File-content I/O cost is bounded: only extensionless executable files trigger a `read(256)`. Unsupported text files (no extension, no exec bit, or non-shell shebang) remain silently ignored — no warnings.
- New adapter implementation in `src/sdi/parsing/shell.py` (model after `src/sdi/parsing/go.py`):
  - Implement `ShellAdapter(LanguageAdapter)` using `tree_sitter_bash`. `language_name` returns `"shell"` for all supported extensions. `file_extensions = frozenset({".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash"})`.
  - Use the lazy `_PARSER` singleton pattern from `go.py:22-30`. Reuse helpers from `_lang_common.py`: `_structural_hash`, `_location`, `_walk_nodes`, `count_loc`.
  - **Imports / includes** — populate `FeatureRecord.imports` from `command` AST nodes whose `command_name` is `source` or `.`, with a single literal-string argument:
    - Resolve the literal path to a repo-relative POSIX string. If the literal is absolute or starts with `/`, attempt `Path(literal).resolve().relative_to(repo_root)`; on failure, drop the import.
    - If the literal is relative (`./common.sh`, `../lib/util.sh`, `common.sh`), resolve relative to the **importing file's directory**, then `relative_to(repo_root)`. Drop on failure.
    - Skip dynamic forms entirely: any argument containing `$`, backticks, command substitution `$(...)`, glob metacharacters, or word-splitting whitespace. Static literal only.
    - Output format matches what `graph/builder.py` already consumes for file-based languages (the same convention Python uses for resolved relative imports): a repo-relative POSIX path string, e.g. `"src/lib/util.sh"`. Unresolved imports are silently dropped (consistent with existing adapters).
  - **Symbols** — extract from `function_definition` nodes. The name is the `name` field text (`child_by_field_name("name")`). Both shell forms (`foo() { ... }` and `function foo { ... }`) parse to the same `function_definition` node — no special-casing needed. No namespacing; append the bare name to `symbols`.
  - **Pattern instances** — write a private module `src/sdi/parsing/_shell_patterns.py` mirroring `_python_patterns.py` (custom AST walker; do **not** use `categories.py` query strings — see Watch For). Detect:
    - `error_handling`:
      - `command` nodes with `command_name == "set"` whose argument list contains any of `-e`, `-u`, `-o pipefail`, `-eu`, `-eo`, `-uo`, `-euo`, or any `-` flag combination including `e`, `u`, or starting with `-o`.
      - `command` nodes with `command_name == "trap"` whose last argument is `ERR`, `EXIT`, `INT`, `TERM`, or `HUP`.
      - `command` nodes with `command_name in {"exit", "return"}` whose first argument is a numeric literal `!= "0"`.
      - `list` nodes (the `||` and `&&` constructs) whose right side is a `command` with `command_name in {"exit", "return", "false"}`.
    - `logging`:
      - `command` nodes with `command_name in {"echo", "printf", "logger", "tee"}`.
    - **Structural hash composition for shell:** because `command` nodes share the same node type regardless of `command_name`, fold `command_name` into the structural fingerprint when emitting an instance. Implement a `_shell_structural_hash(node)` helper in `_shell_patterns.py` that, for `command` nodes, prepends `command_name` text to the serialization before hashing; falls back to `_lang_common._structural_hash` for non-command nodes. This keeps `set -e`, `trap ERR`, and `exit 1` as distinct shapes.
  - **Pattern category registration** — add a decorative `_SHELL_QUERIES: dict[str, str] = {}` plus a shell entry in the per-language registry inside `src/sdi/patterns/categories.py:46-122` for parity. Leave `_SHELL_QUERIES` empty in v1 — the actual extraction lives in `_shell_patterns.py`. This keeps `categories.py` aware of shell as a registered language without misleading query strings.
- Runner registration in `src/sdi/parsing/_runner.py`:
  - Append `("shell", "sdi.parsing.shell", "ShellAdapter")` to `_adapter_modules` in `_register_adapters` (`_runner.py:28-35`). No other changes needed — the existing `try/except ImportError` block at lines 37-44 produces the warning automatically.
- Parse cache (`src/sdi/parsing/_parse_cache.py`):
  - **No changes required.** The cache is keyed on file content SHA-256 and is language-agnostic; shell `FeatureRecord`s round-trip through the existing read/write paths automatically. Mention only to pre-empt over-engineering.
- Test conftest (`tests/conftest.py`):
  - Add `_has_shell_adapter()` and `requires_shell_adapter` markers mirroring `_has_python_adapter` / `requires_python_adapter` at `conftest.py:28-56`. Every shell-touching test must be gated by `requires_shell_adapter`.
- Fixture and test coverage:
  - Add `tests/fixtures/simple-shell/` with **3 scripts** (≈10–20 LOC each):
    - `deploy.sh`: starts with `set -euo pipefail`, contains `source ./lib/util.sh`, defines one function, has one `echo` and one `logger` call, includes one `trap cleanup ERR`.
    - `lib/util.sh`: defines two functions, contains one `printf`-based logging call, no error handling.
    - `extensionless-script` (no extension, exec bit set, shebang `#!/usr/bin/env bash`): defines one function and one `echo`.
  - Add `tests/unit/test_shell_adapter.py` (gated by `requires_shell_adapter`):
    - import/include extraction: literal `source ./x.sh` and `. ./x.sh` resolve to repo-relative paths.
    - dynamic-source rejection: `source "$DIR/x.sh"`, `source $(which foo)`, and `source ${LIB}/x.sh` produce zero imports.
    - function symbol extraction: both `foo() { ... }` and `function foo { ... }` add `foo` to `symbols`.
    - error_handling instances: `set -e`, `set -euo pipefail`, `trap cleanup ERR`, and `exit 1` each produce one instance with distinct `ast_hash` values.
    - logging instances: `echo`, `printf`, and `logger` calls each produce one `logging` instance with distinct `ast_hash` values.
    - empty file → zero instances, zero imports, zero symbols, no exception.
    - syntactically broken script → adapter emits warning via `parse_file_safe`, returns `None`, no exception escapes.
    - structural-hash stability: parsing the same script bytes twice yields identical `ast_hash` values for every instance.
  - Extend `tests/unit/test_discovery.py`:
    - extensions `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash` map to `"shell"`.
    - `.fish` does **not** map to `"shell"` (returns `None` from `detect_language`).
    - extensionless executable file with `#!/usr/bin/env bash` is discovered as `("shell", path)`.
    - extensionless executable file with `#!/usr/bin/env python3` is **not** discovered (returns nothing).
    - extensionless file without exec bit but with `#!/bin/bash` shebang is **not** discovered.
    - file with `.txt` extension and `#!/bin/bash` shebang is **not** discovered (extension takes precedence; no content read).
  - Extend `tests/integration/test_full_pipeline.py`:
    - Add a test class gated by `requires_shell_adapter` that points `parse_repository` at `tests/fixtures/simple-shell/` and asserts `language_breakdown["shell"] == 3`, the expected `symbols` count, and at least one `error_handling` and one `logging` pattern instance in the resulting catalog.
- Documentation:
  - Add a one-line entry under the "Unreleased" / next-version heading in `CHANGELOG.md`: `Added: shell language support (.sh/.bash/.zsh/.ksh and shebang detection) via tree-sitter-bash.`

**Acceptance criteria:**
- `sdi snapshot` on `tests/fixtures/simple-shell/` (no custom config) reports `language_breakdown["shell"] == 3` and produces a non-empty pattern catalog.
- Extensionless executable scripts with allow-listed shell shebangs are discovered as `("shell", path)`; non-shell shebangs are ignored without warning.
- With `tree-sitter-bash` not installed, `_register_adapters` emits one `[warning] Shell adapter unavailable: ...` to stderr and the snapshot completes (no crash) when other grammars are available.
- `FeatureRecord.language == "shell"` for every parsed shell file regardless of extension.
- Static `source` / `.` imports resolve to repo-relative POSIX paths; dynamic forms produce zero imports and no warnings.
- All new unit and integration tests pass on Python 3.10, 3.11, and 3.12.
- `mypy src/sdi/` passes with `tree-sitter-bash` either present or absent.
- No regressions: existing fixture-based snapshot/catalog tests for Python/TS/JS/Go/Java/Rust produce byte-identical `language_breakdown` keys for non-shell fixtures.

**Tests:** (full enumerated assertions are listed under "Fixture and test coverage" above; this section is a checklist of the test files touched)

- `tests/unit/test_discovery.py` — six new cases (extensions, fish exclusion, shebang positive, shebang negative on python, no-exec-bit, extension-takes-precedence).
- `tests/unit/test_shell_adapter.py` — eight cases (imports, dynamic rejection, both function forms, four error_handling shapes, three logging shapes, empty file, broken script, hash stability).
- `tests/integration/test_full_pipeline.py` — one new class gated by `requires_shell_adapter` asserting `language_breakdown["shell"] == 3` and presence of `error_handling` + `logging` instances.

**Watch For:**
- **Do not use `categories.py` query strings for extraction.** The `_PYTHON_QUERIES` strings at `src/sdi/patterns/categories.py:46-82` are decorative and unused at runtime — actual extraction lives in per-language walker modules (`_python_patterns.py` and the `_extract_patterns` function in `go.py:156-183`; Java/Rust/JS/TS adapters follow the same custom-walker convention with no query strings registered at all). Follow that convention for shell: walker code in `_shell_patterns.py`, `_SHELL_QUERIES = {}` left empty.
- **`set -e` family fingerprint coarseness.** Tree-sitter-bash represents shell builtins as `command` nodes; without folding `command_name` into the structural hash, every `set -e` / `set -u` / `set -o pipefail` collapses to the same shape. The `_shell_structural_hash` helper specified in the adapter section is mandatory, not optional — otherwise `error_handling` entropy will under-count.
- **Shebang detection is the only file-content I/O during discovery.** Bound it: extensionless files only, exec bit required, 256-byte read max, first line only. Any cost growth here regresses parse latency.
- **Allow-list shebang interpreters strictly.** Match path tokens, not substrings — otherwise `#!/usr/bin/env bashbrew` would be miscategorized. Use `Path(interp).name in {"sh","bash","zsh","ksh","dash","ash"}`.
- **Static-only `source` resolution.** Drop any `source` argument containing `$`, backticks, `$(...)`, glob chars, or whitespace splits. Capturing dynamic forms produces phantom edges and breaks reproducibility.
- **`.fish` is intentionally unsupported.** Fish syntax differs from POSIX/bash and tree-sitter-bash will produce malformed ASTs. Map `.fish` to no language so it surfaces in the existing "no grammar" warning rather than corrupting analysis silently.
- **Determinism guarantees:** no shell execution, no env-var expansion, no filesystem traversal beyond the parsed file's directory.

**Seeds Forward:**
- Enables SDI coverage for shell-heavy repos (high-impact for Tekhton-scale script surfaces).
- Establishes shell AST substrate needed for richer pattern fingerprints and better drift signal quality in Milestone 14.
- Unblocks future support for script-centric boundary inference in ops/infrastructure codebases.

---
