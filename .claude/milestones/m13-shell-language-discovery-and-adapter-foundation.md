### Milestone 13: Shell Language Discovery and Adapter Foundation
<!-- milestone-meta
id: "13"
status: "planned"
-->


**Scope:** Add first-class shell parsing support to SDI's Stage 1 pipeline so shell scripts are discovered, parsed, and represented as FeatureRecords with deterministic behavior and graceful degradation when grammar dependencies are missing.

**Deliverables:**
- Shell grammar dependency wiring:
  - Add `tree-sitter-bash` (or equivalent maintained shell grammar package compatible with tree-sitter >=0.24) to `pyproject.toml` optional `all` extras.
  - Ensure import failure is treated as a warning path (consistent with existing language adapters).
- Discovery updates in `src/sdi/parsing/discovery.py`:
  - Extend extension mapping for shell files: `.sh`, `.bash`, `.zsh`, `.ksh`, `.fish`.
  - Add shebang-based detection for extensionless executable scripts (for example: `#!/usr/bin/env bash`, `#!/bin/sh`, `#!/usr/bin/env zsh`).
  - Keep unsupported files silent (no noisy warnings for non-code assets).
- New adapter implementation in `src/sdi/parsing/shell.py`:
  - Implement `ShellAdapter(LanguageAdapter)` using tree-sitter shell grammar.
  - Extract imports/includes from shell constructs (`source`, `.`) where statically resolvable.
  - Extract symbols from function definitions with normalized names.
  - Emit baseline pattern instances for at least:
    - `error_handling` (for example: `set -e`, `trap ... ERR`, explicit exit guards)
    - `logging` (for example: `echo`, `printf`, `logger` call sites)
- Runner registration in `src/sdi/parsing/_runner.py`:
  - Register shell adapter in the adapter factory table.
  - Preserve existing behavior for missing grammar: warning + skip.
- Fixture and test coverage:
  - Add `tests/unit/test_shell_adapter.py` with parser, imports, symbols, and basic pattern tests.
  - Extend `tests/unit/test_discovery.py` with shell extension tests and shebang detection tests.
  - Add integration assertion in `tests/integration/test_full_pipeline.py` that shell files are counted when grammar is available.

**Acceptance criteria:**
- `sdi snapshot` discovers and parses shell files in supported extensions without custom config.
- Extensionless executable scripts with shell shebangs are discovered as `shell`.
- Missing shell grammar does not fail snapshot; it emits warning and continues if other grammars are present.
- Shell `FeatureRecord.language` is consistently `"shell"`.
- Imports/includes from `source`/`.` are captured when literal paths are present.
- At least one shell-heavy fixture repo produces non-zero shell file counts in snapshot language breakdown.
- All new unit and integration tests pass on Python 3.10-3.12.

**Tests:**
- `tests/unit/test_discovery.py`:
  - detect `.sh/.bash/.zsh/.ksh/.fish` as shell
  - detect extensionless files by shebang
  - verify non-shell shebangs remain unsupported
- `tests/unit/test_shell_adapter.py`:
  - import/include extraction (`source`, `.`)
  - function symbol extraction
  - baseline pattern extraction (`error_handling`, `logging`)
  - empty/invalid script resilience
- `tests/integration/test_full_pipeline.py`:
  - shell fixture included in parsed file count
  - snapshot command remains successful with mixed-language repository

**Watch For:**
- Tree-sitter shell grammar package naming and API compatibility differ across ecosystems; pin to a tested package and version range.
- Shebang detection must be byte-safe and cheap; only inspect the first line and avoid reading full files during discovery.
- Avoid false positives for text files that start with `#!` but are not shell.
- Shell import/include paths may be dynamic; only capture static literals and skip dynamic expressions.
- Keep adapter deterministic: no shell execution, no environment expansion, no filesystem side effects.

**Seeds Forward:**
- Enables SDI coverage for shell-heavy repos (high-impact for Tekhton-scale script surfaces).
- Establishes shell AST substrate needed for richer pattern fingerprints and better drift signal quality in Milestone 14.
- Unblocks future support for script-centric boundary inference in ops/infrastructure codebases.

---
