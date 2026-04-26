# Coder Summary
## Status: COMPLETE

## What Was Implemented
- **Extracted JS/TS resolver to `src/sdi/graph/_js_ts_resolver.py`**: All JS/TS
  helper functions (`_resolve_js_import`, `_load_ts_path_aliases`, `_match_alias`,
  `_expand_alias_candidates`, `_try_extensions_and_index`, `_strip_jsonc`,
  `_is_js_ts_file`, `_normalize_js_path`, `_build_js_path_set`) and their constants
  moved out of builder.py. All names re-imported at module level in builder.py for
  backward compatibility — existing tests requiring `from sdi.graph.builder import
  _load_ts_path_aliases` (etc.) continue to work unchanged.

- **Added `_SHELL_LANGS`, `_SHELL_EXTENSIONS_FOR_FALLBACK`, `_KNOWN_SHELL_EXTS`
  constants to builder.py**: `_SHELL_EXTENSIONS_FOR_FALLBACK` is a `tuple` (not
  `frozenset`); order `.sh` before `.bash` is intentional and documented in comments.

- **Added `_resolve_shell_import(import_str, path_set)` to builder.py**: Fast-path
  exact match; extension fallback using the ordered tuple only when the literal does
  not already end in a known shell extension.

- **Modified `build_dependency_graph()` shell dispatch arm**: `is_shell` dispatches
  to `_resolve_shell_import` before `is_js_ts` and the Python default. `shell_path_set`
  is built once as `frozenset(path_to_id.keys())` — full set, no language filtering,
  enabling legitimate cross-language `source` edges.

- **Created `tests/fixtures/shell-graph/`**: 8 scripts, 13 explicit `source` edges
  (≥12 acceptance threshold). `lib/common.sh` uses `source ./util` (extensionless)
  which exercises the `.sh` extension fallback → `lib/util.sh`. All 8 files form a
  single weakly-connected component (component_count = 1 ≤ 4).

- **Created `tests/unit/test_graph_builder_shell.py`**: 23 unit tests covering
  exact match, missing import, extensionless-to-sh, sh-vs-bash preference, known
  extension skip, self-import, cross-language source, mixed-language 3-way dispatch,
  weighted duplicate edge, and determinism.

- **Extended `tests/integration/test_shell_pipeline.py`**: Added 3 new test classes
  (`TestShellPipeline.test_edge_count_at_least_one`, `TestShellHeavyGraph`,
  `TestShellGraphFixture`) covering all acceptance criteria from the milestone.

## Root Cause
Shell records fell into the Python (dotted-module-key) resolution branch in
`build_dependency_graph()`. Python resolution matches dotted strings like
`sdi.config` against the module map; shell import strings are repo-relative
POSIX paths like `lib/util.sh` that never match any dotted key. Result: all shell
`source` directives were classified as unresolved, producing edge_count ≈ 0 and
component_count ≈ N for shell-heavy repos. Fix: third dispatch arm with direct path
lookup plus bounded extension fallback.

## Files Modified
- `src/sdi/graph/_js_ts_resolver.py` (NEW) — extracted JS/TS resolver helpers
- `src/sdi/graph/builder.py` — shell dispatch arm, shell constants, `_resolve_shell_import`
- `tests/fixtures/shell-graph/entrypoint.sh` (NEW)
- `tests/fixtures/shell-graph/lib/common.sh` (NEW)
- `tests/fixtures/shell-graph/lib/util.sh` (NEW)
- `tests/fixtures/shell-graph/lib/log.sh` (NEW)
- `tests/fixtures/shell-graph/lib/db.sh` (NEW)
- `tests/fixtures/shell-graph/cmd/deploy.sh` (NEW)
- `tests/fixtures/shell-graph/cmd/rollback.sh` (NEW)
- `tests/fixtures/shell-graph/cmd/status.sh` (NEW)
- `tests/unit/test_graph_builder_shell.py` (NEW)
- `tests/integration/test_shell_pipeline.py` (modified — added M15 test classes)

## Human Notes Status
No Human Notes section present in milestone spec.

## Docs Updated
None — no public-surface changes in this task. `build_dependency_graph()` signature
is unchanged; the shell resolver is an internal dispatch detail.

## Architecture Change Proposals
**Current constraint**: builder.py contains all resolution logic (Python, JS/TS) in
one file.
**What triggered this**: builder.py was 455 lines pre-M15; adding shell resolver would
push it well past the 300-line ceiling.
**Proposed change**: Extracted JS/TS helpers to `src/sdi/graph/_js_ts_resolver.py`.
All names re-exported from builder.py so the public surface of `sdi.graph.builder`
is unchanged.
**Backward compatible**: Yes — `from sdi.graph.builder import _load_ts_path_aliases`
(etc.) still works.
**ARCHITECTURE.md update needed**: No (module is internal with leading underscore).

## Observed Issues (out of scope)
- `tests/unit/test_graph_builder.py`: pre-existing 833-line length violation; new
  shell tests placed in separate file to avoid further growth.
- `tests/integration/test_shell_evolving.py`: module-level `xfail` carry-over from
  M14; unrelated to M15.
