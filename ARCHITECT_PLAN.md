# Architect Plan
**Audit date:** 2026-04-13
**Drift log entries addressed:** 8 (all unresolved observations)

---

## Staleness Fixes
*(route to jr coder)*

- `src/sdi/patterns/catalog.py:40` (`ShapeStats.file_paths` field) — Add a clarifying comment to the field docstring: the in-memory list holds one entry per instance occurrence and may contain duplicates (so `len(file_paths) == instance_count`); `to_dict()` deduplicates via `sorted(set(...))` on serialization, so the persisted form holds unique file paths only. Without this note, `instance_count` and `len(file_paths)` appear to measure the same thing but do not.

---

## Dead Code Removal
*(route to jr coder)*

None.

---

## Naming Normalization
*(route to jr coder)*

1. **`FeatureRecord` import: standardize to `sdi.parsing`** — `tests/unit/test_catalog.py:16` and `tests/unit/test_catalog_velocity_spread.py:14` both import `FeatureRecord` from `sdi.snapshot.model`. `tests/conftest.py:13` correctly imports from `sdi.parsing`. Per CLAUDE.md repo layout, `sdi/parsing/__init__.py` is the documented public API for `FeatureRecord`; `sdi.snapshot.model` is the definition site, not the intended import path. Change both test files to `from sdi.parsing import FeatureRecord`.

2. **Promote duplicated catalog test helpers to `conftest.py`** — `make_record()`, `make_instance()`, and `default_config()` are defined verbatim in both `tests/unit/test_catalog.py:24-49` and `tests/unit/test_catalog_velocity_spread.py:23-44`. Promote all three to `tests/conftest.py`. Reconcile the `make_instance()` signatures: `test_catalog.py` has a `line: int = 1` parameter; `test_catalog_velocity_spread.py` does not. The `test_catalog.py` signature (with default) is the superset — use it. Remove the local definitions from both test files after promoting.

3. **Consolidate `_make_graph` Leiden test helper** — `tests/unit/test_leiden.py:38-43` and `tests/unit/test_leiden_internals.py:37-41` define identical `_make_graph(n, edges)` helpers. Move the shared helper to a new `tests/unit/helpers.py` module and import from there in both test files. Do not add it to `conftest.py` — it is igraph-specific and only relevant to Leiden tests; adding an igraph import to the top-level conftest couples all test collection to igraph availability.

---

## Simplification
*(route to sr coder)*

1. **Extract `resolve_snapshots_dir` helper — apply to all 6 CLI commands** — `src/sdi/snapshot/assembly.py:127-130` already guards `snapshots_dir` construction with an `is_relative_to` bounds check. The six M08 CLI commands construct `snapshots_dir = repo_root / config.snapshots.dir` with no equivalent check: `snapshot_cmd.py:184`, `show_cmd.py:117`, `diff_cmd.py:121`, `trend_cmd.py:84`, `check_cmd.py:166`, `catalog_cmd.py:102`. Add a `resolve_snapshots_dir(repo_root: Path, config: SDIConfig) -> Path` helper to `src/sdi/cli/_helpers.py` that mirrors the `assembly.py` guard (resolves the path, checks `is_relative_to`, raises `SystemExit(2)` with a descriptive message if the check fails). Replace the bare `repo_root / config.snapshots.dir` in all six commands with a call to this helper. This makes the guard uniform and eliminates the six unguarded call sites that the security agent flagged in `assembly.py`.

2. **`_count_boundary_violations` default of 1 → 0** — `src/sdi/snapshot/delta.py:102`: `int(e.get("count", 1))` silently treats an edge dict with a missing `count` key as one crossing. The `inter_cluster_edges` structure produced by `_compute_inter_cluster_edges` always includes `count`, so this default only fires on schema deviations or old snapshot data. Using 1 inflates the violation count; using 0 is the safe default (an unknown count contributes nothing). Change to `int(e.get("count", 0))` and add a comment on the line: `# count absent in malformed data → treat as 0 (conservative)`.

3. **`_load_pair` partial-ref behavior must be explicit** — `src/sdi/cli/diff_cmd.py:44-66`: `_load_pair` enters the `else` branch when *either* `ref_a` or `ref_b` is non-None. `resolve_snapshot_ref` resolves `None` to the latest snapshot (`_helpers.py:87-88`). The result: `sdi diff snap1` silently diffs `snap1` against the latest, which is non-obvious and undocumented. Add a guard at the top of the `else` branch: if exactly one of `ref_a`/`ref_b` is `None`, emit `[error] Specify both SNAPSHOT_A and SNAPSHOT_B, or omit both to diff the last two snapshots.` and raise `SystemExit(1)`. Update the command docstring to document this constraint.

4. **Eliminate mutable `_null_divergence()` placeholder in `assemble_snapshot`** — `src/sdi/snapshot/assembly.py:136-150`: `snap` is constructed with a throwaway `_null_divergence()` value that is immediately overwritten by `snap.divergence = compute_delta(snap, previous)`. All inputs to `compute_delta` (`pattern_catalog`, `graph_metrics`, `partition_data`, `snapshot_version`) are available before `Snapshot` construction. Restructure `assemble_snapshot` to call `_load_previous(snapshots_dir)` before constructing `snap`, build `snap` with the actual divergence in a single assignment, and remove the `_null_divergence()` function. If `compute_delta`'s current `Snapshot`-typed signature makes single-pass construction awkward, the sr coder may use `dataclasses.replace(snap, divergence=compute_delta(snap, previous))` as an intermediate step, provided no second mutable post-construction assignment remains.

---

## Design Doc Observations
*(route to human via HUMAN_ACTION_REQUIRED.md)*

None.

---

## Drift Observations to Resolve

The following DRIFT_LOG.md entries are addressed by this plan and should be marked RESOLVED after implementation:

- `[2026-04-11 | "M08"]` — `snapshot_cmd.py:184`, `show_cmd.py:117`, `diff_cmd.py:121`, `trend_cmd.py:84`, `check_cmd.py:166`, `catalog_cmd.py:102` path bounds check — addressed by Simplification item 1
- `[2026-04-11 | "M08"]` — `diff_cmd.py:22-66` `_load_pair` partial-spec implicit behavior — addressed by Simplification item 3
- `[2026-04-11 | "M07"]` — `delta.py:102` `count` default of 1 — addressed by Simplification item 2
- `[2026-04-11 | "M07"]` — `assembly.py:136-150` mutable null divergence placeholder — addressed by Simplification item 4
- `[2026-04-11 | "M06"]` — `test_catalog.py:24-49` and `test_catalog_velocity_spread.py:23-44` duplicated helpers — addressed by Naming Normalization item 2
- `[2026-04-11 | "M06"]` — `FeatureRecord` import location disagreement — addressed by Naming Normalization item 1
- `[2026-04-11 | "M06"]` — `ShapeStats.file_paths` undocumented semantics — addressed by Staleness Fixes item 1
- `[2026-04-11 | "M05"]` — `test_leiden.py` and `test_leiden_internals.py` `_make_graph` duplication — addressed by Naming Normalization item 3

---

## Out of Scope

None — all eight unresolved observations are addressed in this cycle.
