### Milestone 15: Shell Dependency Edge Resolution in Graph Builder
<!-- milestone-meta
id: "15"
status: "pending"
-->


**Scope:** Wire shell adapter output into the dependency graph so static `source` / `.` directives produce real edges. M13 shipped per-file extraction of resolved repo-relative POSIX paths in `FeatureRecord.imports`. `build_dependency_graph` (`src/sdi/graph/builder.py:411-421`) currently dispatches resolution two ways — TS/JS path-based and Python dotted-module-key — and shell falls into the Python branch where its path-shaped strings never match the module map. Result: shell-heavy repos report ~0 edges, ~N components, and ~N clusters, which makes coupling, community detection, and boundary-violation signals all degenerate. This milestone closes that gap with a third dispatch arm.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 3, same commit + same config + same boundaries must produce the same snapshot. The extension fallback added here must be deterministic — a fixed allow-list, ordered, never iteration over a set. Per Rule 9, no command modifies the working tree; the graph builder reads only from the in-memory `path_to_id` set, never the filesystem. The shell adapter already pre-resolves source paths against the importing file's directory; the graph builder's job is *lookup only*, never path math.

**Deliverables:**
- New shell resolver in `src/sdi/graph/builder.py`:
  - Add module-level constants near the existing `_JS_TS_LANGS` (`builder.py:38`):
    ```python
    _SHELL_LANGS: frozenset[str] = frozenset({"shell"})
    _SHELL_EXTENSIONS_FOR_FALLBACK: tuple[str, ...] = (".sh", ".bash")
    ```
    Order is significant — `.sh` is checked before `.bash`. Do **not** include `.zsh`, `.ksh`, `.dash`, or `.ash` in the fallback tuple; those are accepted as primary file extensions (per M13) but adding them as fallback targets produces phantom edges in mixed-shebang repos.
  - Add a `_resolve_shell_import(import_str: str, path_set: frozenset[str]) -> str | None` helper:
    1. Fast path: if `import_str in path_set`, return `import_str`.
    2. Fallback: if the literal does not end in any of `(".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash")`, attempt `import_str + ext` for each `ext` in `_SHELL_EXTENSIONS_FOR_FALLBACK`, returning the first match.
    3. Otherwise return `None`.
  - In `build_dependency_graph` (the per-record loop at `builder.py:412-435`), dispatch shell records *before* the existing Python branch:
    ```python
    is_shell = record.language in _SHELL_LANGS
    is_js_ts = record.language in _JS_TS_LANGS

    for import_str in record.imports:
        if is_shell:
            target_path = _resolve_shell_import(import_str, shell_path_set)
        elif is_js_ts:
            ...  # existing
        else:
            target_path = _resolve_import(import_str, module_map)
    ```
  - Build `shell_path_set: frozenset[str] = frozenset(p for p in path_to_id)` once before the loop. Reuse the full `path_to_id` set; do not filter by language. A Python file path that happens to match a shell `source` literal is a real intra-project edge — the cross-language case is rare but legitimate (e.g., a bash script sources a `.env`-style file co-located with a Python service) and the graph builder should not silently drop it.
- No changes required in `src/sdi/parsing/shell.py`. The adapter already produces the shape the new resolver consumes.
- No changes required in `_resolve_import` (the Python module-key resolver) — its behaviour for non-Python files is unchanged.
- Self-import handling, deduplication, and weighted-edge aggregation are shared with the existing branches at `builder.py:430-449`. Do not duplicate that logic in the shell branch.
- Determinism guard — add an explicit comment at the top of `_resolve_shell_import` noting that `_SHELL_EXTENSIONS_FOR_FALLBACK` is intentionally a `tuple` (not a `set`) and that callers must rely on the order. Reviewers commonly "fix" this to a set; the comment exists to deflect that.

**Acceptance criteria:**
- `sdi snapshot` on `tests/fixtures/simple-shell/` (M13 fixture) reports `graph_metrics.edge_count >= 1` (the existing `source ./lib/util.sh` edge resolves).
- `sdi snapshot` on `tests/fixtures/shell-heavy/` (M14 fixture, ≥ 2 cross-script `source` imports) reports `graph_metrics.edge_count >= 2` and `graph_metrics.component_count <= file_count - 1`.
- A new fixture `tests/fixtures/shell-graph/` (8 scripts, ≥ 12 explicit `source` edges spanning relative and `lib/`-style includes) reports `graph_metrics.edge_count >= 12` and `graph_metrics.component_count <= 4`.
- Implicit-extension test: a script with `source ./common` (no extension) resolves to `common.sh` if that file exists; with both `common.sh` and `common.bash` present, resolution prefers `common.sh`.
- Determinism: parsing and building the graph twice on the same fixture inputs produces byte-identical `graph_metrics` dicts and byte-identical `partition_data.inter_cluster_edges` lists.
- **No regression on non-shell languages.** Run the pre-M15 suite, capture `graph_metrics` for every fixture-based snapshot test (Python/TS/JS/Go/Java/Rust). Post-M15, every value in those captured `graph_metrics` dicts must be byte-identical except where the fixture itself contains shell files.
- `unresolved_count` for shell records correctly reflects unresolved `source` literals (e.g., a literal pointing at a path outside `path_to_id` increments `unresolved_count` by exactly 1).

**Tests:** (gate every shell-touching test with `requires_shell_adapter` from `tests/conftest.py`, established in M13)

- `tests/unit/test_graph_builder.py` — extend with:
  - shell record whose `imports = ["lib/util.sh"]` and `path_to_id` contains `"lib/util.sh"` produces exactly one edge `(record_idx → util_idx)`.
  - shell record whose `imports = ["lib/missing.sh"]` produces zero edges and `metadata["unresolved_count"] == 1`.
  - shell record whose `imports = ["common"]` resolves to `common.sh` when only `common.sh` is in the path set.
  - shell record whose `imports = ["common"]` resolves to `common.sh` (not `common.bash`) when both are in the path set — assert the chosen target explicitly, do not just check non-`None`.
  - shell record whose `imports = ["common.sh"]` resolves to `common.sh` directly without extension fallback (literal-match takes precedence).
  - shell record self-loop: `imports = [its own file_path]` increments `metadata["self_import_count"]` by 1, produces no edge.
  - mixed-language input: a single `build_dependency_graph` call with one Python record + one shell record + one TS record each producing one edge via their respective resolvers — verify the graph has exactly 3 edges with the expected `(src, tgt)` pairs.
  - cross-language `source`: a shell record `imports = ["scripts/env.py"]` with `scripts/env.py` in the path set produces an edge (the cross-language case is supported, not silently dropped).
  - extension-fallback negative case: shell record whose `imports = ["common.zsh"]` does **not** resolve via fallback to `common.sh` (the literal already has a known shell extension; fallback is skipped).
  - determinism: build the graph twice on the same record list, assert `g.get_edgelist()` is identical and `vs["name"]` ordering is identical.
- New fixture `tests/fixtures/shell-graph/` containing:
  - 8 scripts: `entrypoint.sh`, `lib/common.sh`, `lib/util.sh`, `lib/log.sh`, `lib/db.sh`, `cmd/deploy.sh`, `cmd/rollback.sh`, `cmd/status.sh`.
  - `entrypoint.sh` sources `lib/common.sh` and `cmd/deploy.sh`, `cmd/rollback.sh`, `cmd/status.sh`.
  - Each `cmd/*.sh` sources `lib/common.sh` and `lib/log.sh`; `cmd/deploy.sh` and `cmd/rollback.sh` additionally source `lib/db.sh`.
  - `lib/common.sh` sources `lib/log.sh`.
  - At least one script uses `source ./common` (no extension) targeting `lib/common.sh` to exercise the fallback.
  - Total: 12 explicit `source` edges (count manually in the fixture README; assert in the test).
- `tests/integration/test_full_pipeline.py` — extend the shell-adapter-gated class with one assertion per acceptance criterion: `edge_count >= 12` and `component_count <= 4` on `shell-graph/`.
- Reference snapshot: before M15 lands, capture `graph_metrics` JSON for every existing fixture test and store under `tests/fixtures/_reference/graph_metrics_pre_m15/`. M15's regression test reads those references and asserts byte equality against post-M15 output. Delete the reference directory at the end of the milestone (it is throwaway scaffolding, not a permanent fixture).

**Watch For:**
- **The shell adapter already resolves paths.** Do not re-resolve in the graph builder. The import string is already a repo-relative POSIX path or already-failed dynamic form; the graph builder's job is direct lookup plus bounded extension fallback only.
- **Extension fallback is bounded by the allow-list.** `.sh` and `.bash` only, in that order. Reviewers commonly suggest expanding to all six shell extensions or using iteration over `frozenset({...})`. Both expansions inflate phantom-edge risk and break determinism — reject them. The allow-list is a tuple, deliberately.
- **No content-dependent fallback.** Do not read file contents from the filesystem during graph resolution. Discovery already established language at parse time; the graph builder operates only on `path_to_id`.
- **Cross-language `source` is legitimate.** A bash script sourcing a `.env`-style co-located file that happens to be a Python file in the path set should produce an edge. Do not filter `shell_path_set` by language — use the full set.
- **Self-imports are still skipped.** Honor the existing `tgt_id == src_id` skip and increment of `self_import_count` (`builder.py:430`). The shell branch shares this behaviour.
- **Function-call edges are out of scope.** Edges in v0/v1 represent *file inclusion*, not function-call relationships. A future milestone may introduce a separate edge kind for cross-file function references — that work is **not** part of M15. Reviewers may suggest adding it; defer to a future milestone with explicit scope.
- **Empty `imports`.** A shell record with `imports == []` (the common case for leaf scripts) must not produce any spurious lookups. Verify in tests.
- **Determinism is bit-stable.** The unit test that builds the graph twice must compare `g.get_edgelist()` exactly, not just `len()`. If the test passes on length alone, the determinism rule is not actually verified.
- **Weighted edges path.** When `config.boundaries.weighted_edges = true`, the shell branch participates in `edge_weight_map` aggregation identically to the other branches. Add one weighted-edges unit case asserting the weight count for a duplicated `source` literal in the same file equals the duplicate count.

**Seeds Forward:**
- Restores `coupling_topology` and `boundary_violations` as meaningful signals on shell-heavy codebases — Leiden cannot return useful clusters when `edge_count == 0`.
- Provides realistic input for M16's per-language pattern catalog scoping. Without edges, M16's per-language signals would still be technically computable but would never exercise the cross-cluster boundary-spread logic.
- Establishes the third dispatch arm pattern, which future adapter milestones (Ruby `require_relative`, Lua `require`, etc.) can reuse if those adapters likewise pre-resolve imports to repo-relative paths.

---
