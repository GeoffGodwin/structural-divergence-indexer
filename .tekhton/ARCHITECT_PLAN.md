# Architect Plan
**Audit date:** 2026-04-23
**Runs audited:** 8 (observations from M05–M08)

---

## Staleness Fixes
*(route to jr coder)*

- Add field docstring to `src/sdi/patterns/catalog.py:ShapeStats.file_paths` — in-memory list accumulates one entry per occurrence and may contain duplicates; `to_dict()` deduplicates via `sorted(set(...))` on serialization, so `instance_count` and `len(file_paths)` measure different things (occurrences vs unique files). This distinction is currently undocumented on the field. Add: `# one path per occurrence; may contain duplicates — to_dict() deduplicates on write`.

---

## Dead Code Removal
*(route to jr coder)*

None.

---

## Naming Normalization
*(route to jr coder)*

- Normalize `FeatureRecord` import in test files: `tests/unit/test_catalog.py:16` and `tests/unit/test_catalog_velocity_spread.py:14` import `FeatureRecord` from `sdi.snapshot.model` (implementation site); `tests/conftest.py:13` imports from `sdi.parsing` (the public re-export). `sdi/parsing/__init__.py` explicitly re-exports `FeatureRecord` as the module's public API. Change both test files to `from sdi.parsing import FeatureRecord` to agree with `conftest.py` and the public-API contract.

---

## Simplification
*(route to sr coder)*

- **Path bounds check — 6 CLI commands** (`snapshot_cmd.py:184`, `show_cmd.py:117`, `diff_cmd.py:121`, `trend_cmd.py:84`, `check_cmd.py:166`, `catalog_cmd.py:102`) each compute `snapshots_dir = repo_root / config.snapshots.dir` with no path bounds check. The same check already exists in `assembly.py:127-130` (`is_relative_to`). Extract a helper `resolve_snapshots_dir(repo_root: Path, config: SDIConfig) -> Path` into `src/sdi/cli/_helpers.py` that performs the `is_relative_to` guard and raises `SystemExit(2)` on violation. Replace the bare path join in all six commands with a call to this helper.

- **`diff_cmd.py:_load_pair` partial-ref implicit behavior** (`diff_cmd.py:44-59`) — when exactly one of `ref_a`/`ref_b` is `None`, the `else` branch calls `resolve_snapshot_ref(snapshots_dir, None)`, which silently resolves `None` to the latest snapshot, treating a partial two-arg spec as a full diff. This is undocumented and likely a user error. Add an explicit guard at the top of the `else` block: `if (ref_a is None) != (ref_b is None): click.echo("[error] Provide both SNAPSHOT_A and SNAPSHOT_B, or neither.", err=True); raise SystemExit(2)`. Update the function docstring to reflect that `ref_a` and `ref_b` must both be `None` or both be non-`None`.

- **`delta.py:102` default count=1** — `sum(int(e.get("count", 1)) for e in edges)` defaults a missing `count` key to 1 (treating any count-less edge as one crossing). An edge dict present without a `count` key is either a data bug or should contribute 0 to the total. Change the default to `0`. If the partition serialization contract guarantees `count` is always present (it is — see `assembly.py:_partition_data` and `leiden.py:_compute_inter_cluster_edges`), add an `assert "count" in e` with a descriptive message instead, so missing count keys surface immediately rather than silently.

- **`assembly.py:136-150` mutable placeholder** — `snap` is constructed with a `_null_divergence()` placeholder then immediately mutated on the next line via `snap.divergence = compute_delta(snap, previous)`. All data needed for `compute_delta` (the three dicts: `pattern_catalog`, `graph_metrics`, `partition_data`) is available before `Snapshot` construction. Refactor: move `previous = _load_previous(snapshots_dir)` above the `Snapshot(...)` call; build `snap` with `divergence=_null_divergence()`; then replace with `snap = dataclasses.replace(snap, divergence=compute_delta(snap, previous))`. This eliminates the mutation pattern and makes `snap` effectively immutable after initial construction. Requires `import dataclasses` in `assembly.py`.

- **Test helper consolidation — catalog tests** (`tests/unit/test_catalog.py:24-49`, `tests/unit/test_catalog_velocity_spread.py:23-44`) — `make_record()`, `make_instance()`, and `default_config()` are duplicated verbatim across both files. (Note: `test_catalog.py:36`'s `make_instance` takes an optional `line=1` parameter that `test_catalog_velocity_spread.py:35`'s copy omits — the consolidated version should accept `line: int = 1`.) Promote all three functions to `tests/conftest.py` (where `sample_pattern_catalog` and `sample_community_result` already live). Delete the local copies from both test files. No test logic changes.

- **Test helper consolidation — leiden tests** (`tests/unit/test_leiden.py:38-43`, `tests/unit/test_leiden_internals.py:37-43`) — `_make_graph(n, edges)` is duplicated verbatim. Promote to `tests/conftest.py` or a new `tests/unit/helpers.py`; import from there in both test files. Delete the local copies. No test logic changes.

---

## Design Doc Observations
*(route to human via HUMAN_ACTION_REQUIRED.md)*

None.

---

## Drift Observations to Resolve

The following entries from `DRIFT_LOG.md` are addressed by this plan and should be marked **RESOLVED** after implementation:

- `[2026-04-11 | "M08"]` `snapshot_cmd.py:184`, `show_cmd.py:117`, `diff_cmd.py:121`, `trend_cmd.py:84`, `check_cmd.py:166`, `catalog_cmd.py:102` — All six new M08 CLI commands construct `snapshots_dir = repo_root / config.snapshots.dir` with no path bounds check.
- `[2026-04-11 | "M08"]` `diff_cmd.py:22-66` — `_load_pair` only handles the case where both refs are None or both are non-None; partial spec silently treated as full diff.
- `[2026-04-11 | "M07"]` `delta.py:102` — `int(e.get("count", 1))` with a default of 1 instead of 0.
- `[2026-04-11 | "M07"]` `assembly.py:136-150` — `snap` constructed with throwaway `_null_divergence()` placeholder immediately overwritten.
- `[2026-04-11 | "M06"]` `tests/unit/test_catalog.py:24-49` and `tests/unit/test_catalog_velocity_spread.py:23-44` — `make_record()`, `make_instance()`, and `default_config()` helpers duplicated verbatim.
- `[2026-04-11 | "M06"]` `sdi.snapshot.model.FeatureRecord` vs `sdi.parsing.FeatureRecord` — test files disagree on canonical import location.
- `[2026-04-11 | "M06"]` `ShapeStats.to_dict()` deduplicates `file_paths` on serialization but in-memory list may contain duplicates; undocumented.
- `[2026-04-11 | "M05"]` `test_leiden.py:36-40` and `test_leiden_internals.py:36-40` — `_make_graph` helper duplicated verbatim.

---

## Out of Scope

None. All eight unresolved observations are bounded, actionable, and included above.
