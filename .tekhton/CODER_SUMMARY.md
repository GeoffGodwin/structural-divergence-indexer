# Coder Summary
## Status: COMPLETE

## What Was Implemented

Milestone 13: Shell Language Discovery and Adapter Foundation.

- **`pyproject.toml`**: Added `tree-sitter-bash` to `[project.optional-dependencies] all` and to `[[tool.mypy.overrides]] module` list.
- **`src/sdi/parsing/discovery.py`**: Extended `_EXTENSION_TO_LANGUAGE` with `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash` → `"shell"`. Added `_SHELL_INTERPRETERS` frozenset. Added `_detect_shell_shebang(path)` private helper for extensionless executable scripts (256-byte read, first-line-only, allow-list token matching via `Path.name`). Integrated shebang check into `discover_files` after gitignore/exclude filtering: extensionless files with exec bit invoke shebang detection.
- **`src/sdi/parsing/_shell_patterns.py`** (NEW): Shell pattern extraction module. Implements `_shell_structural_hash` (folds command_name into hash for command nodes so `set -e`, `trap ERR`, `exit 1` get distinct fingerprints), `extract_pattern_instances` (detects `error_handling` and `logging`), and `count_loc_shell`. Error-handling detection covers: `set -e/u/o` family, `trap ERR/EXIT/INT/TERM/HUP`, `exit/return` non-zero literal, `||/&&` list nodes with bail commands on right side.
- **`src/sdi/parsing/shell.py`** (NEW): `ShellAdapter(LanguageAdapter)` using tree-sitter-bash. Lazy `_PARSER` singleton pattern. `_extract_imports` resolves static `source`/`.` includes to repo-relative POSIX paths, silently dropping dynamic forms (non-`word` arg types). `_extract_symbols` walks `function_definition` nodes (both `foo() {}` and `function foo {}` forms). Delegates pattern extraction to `_shell_patterns.py`.
- **`src/sdi/parsing/_runner.py`**: Appended `("shell", "sdi.parsing.shell", "ShellAdapter")` to `_adapter_modules` list. Existing `try/except ImportError` block emits warning automatically when tree-sitter-bash is absent.
- **`src/sdi/patterns/categories.py`**: Added `_SHELL_QUERIES: dict[str, str] = {}` (empty — actual extraction is in `_shell_patterns.py`). Updated `_build_registry` to register shell queries for parity.
- **`tests/conftest.py`**: Added `_has_shell_adapter()` and `requires_shell_adapter` marker mirroring the existing python/ts guards.
- **`tests/fixtures/simple-shell/deploy.sh`** (NEW): ~18 LOC fixture with `set -euo pipefail`, `source ./lib/util.sh`, `trap cleanup ERR`, function definition, `echo`, `logger`.
- **`tests/fixtures/simple-shell/lib/util.sh`** (NEW): ~12 LOC fixture with two functions and `printf` logging.
- **`tests/fixtures/simple-shell/extensionless-script`** (NEW): Exec-bit set, `#!/usr/bin/env bash` shebang, one function, one `echo`.
- **`tests/unit/test_shell_adapter.py`** (NEW): 8 test classes covering import extraction, dynamic rejection, both function forms, 4 error_handling shapes, 3 logging shapes, empty file, broken script (no exception escape), and hash stability.
- **`tests/unit/test_discovery.py`**: Extended with `TestShellExtensions` (7 cases: 6 extensions + fish exclusion) and `TestShebangDetection` (4 cases: env bash discovered, env python3 rejected, no exec bit rejected, txt extension takes precedence).
- **`tests/integration/test_shell_pipeline.py`** (NEW): Dedicated integration test file (70 lines) with `TestShellPipeline` asserting `language_breakdown["shell"] == 3` and presence of `error_handling` + `logging` categories.
- **`CHANGELOG.md`**: Added shell support entry under `[Unreleased]`.

## Root Cause (bugs only)
N/A — feature implementation.

## Files Modified

- `pyproject.toml` — added tree-sitter-bash dependency and mypy override
- `src/sdi/parsing/discovery.py` — shell extensions + shebang detection
- `src/sdi/parsing/_shell_patterns.py` (NEW) — shell pattern extraction
- `src/sdi/parsing/shell.py` (NEW) — ShellAdapter
- `src/sdi/parsing/_runner.py` — shell adapter registration
- `src/sdi/patterns/categories.py` — _SHELL_QUERIES declaration + registry update
- `tests/conftest.py` — _has_shell_adapter + requires_shell_adapter
- `tests/fixtures/simple-shell/deploy.sh` (NEW) — fixture script
- `tests/fixtures/simple-shell/lib/util.sh` (NEW) — fixture library
- `tests/fixtures/simple-shell/extensionless-script` (NEW) — shebang fixture
- `tests/unit/test_shell_adapter.py` (NEW) — 22 unit tests
- `tests/unit/test_discovery.py` — 11 new test cases
- `tests/integration/test_shell_pipeline.py` (NEW) — 2 integration tests
- `CHANGELOG.md` — unreleased entry

## Human Notes Status
No Human Notes section in this task.

## Observed Issues (out of scope)
- `src/sdi/parsing/_python_patterns.py:139` — `in_multiline_string` variable declared but never used (pre-existing ruff F841)
- `src/sdi/parsing/_python_patterns.py:78` — line too long in data_methods dict (pre-existing ruff E501)
- `src/sdi/parsing/python.py` — `hashlib` and `sys` imports unused (pre-existing ruff F401)
- `src/sdi/parsing/javascript.py` — `node_text` import unused (pre-existing ruff F401)
- `src/sdi/parsing/_lang_common.py:40` — `_walk_nodes` missing return type annotation (pre-existing mypy)
- `src/sdi/parsing/typescript.py:49,75` — missing type annotations (pre-existing mypy)

## Docs Updated
`CHANGELOG.md` — added shell support entry under `[Unreleased]`.
