# Drift Log

## Metadata
- Last audit: never
- Runs since audit: 5

## Unresolved Observations
- [2026-04-11 | "Address all 8 open non-blocking notes in NON_BLOCKING_LOG.md. Fix each item and note what you changed."] `src/sdi/parsing/go.py:19` and `src/sdi/parsing/rust.py:23` — both adapters still import `FeatureRecord` from `sdi.snapshot.model` directly, while Item 8 established `sdi.parsing` as the canonical import path for tests. Creates a split convention across the codebase; the adapters are the primary producers of FeatureRecord and should arguably follow the same convention.
- [2026-04-11 | "Address all 8 open non-blocking notes in NON_BLOCKING_LOG.md. Fix each item and note what you changed."] `src/sdi/graph/metrics.py:85` / `src/sdi/graph/builder.py:203` — bare `dict` return type annotations remain in two places after the narrowing work in Item 2; suggests a sweep of all bare `dict`/`list` return types would clean up the module.
- [2026-04-11 | "M04"] `src/sdi/graph/builder.py:59` — The `src.` prefix strip in `_file_path_to_module_key` is unconditional and would silently mishandle a project that has a legitimate top-level package named `src`. No action needed now, but the assumption should be documented in the function docstring.
- [2026-04-11 | "M04"] Security agent LOW finding (`metrics.py:130`, `graph.simple_cycles()` exponential worst-case) remains unaddressed. Acceptable for v1 on real codebases, but should be tracked in the hardening backlog.
- [2026-04-10 | "M03"] `_structural_hash`, `_location`, `_walk_nodes`, and `count_loc` are copy-pasted verbatim into `go.py`, `java.py`, and `rust.py`. These are already extracted into `_js_ts_common.py` for the JS/TS adapters. A future `_lang_common.py` (or moving them to `base.py`) would eliminate this triplication.
- [2026-04-10 | "M03"] `go.py:130-131`: `elif node.type in ("method_declaration",):` — single-element tuple in `in` check is redundant; should be `node.type == "method_declaration"`. Cosmetic but worth cleanup.
- [2026-04-10 | "M01"] `src/sdi/snapshot/model.py:5-6` — Comment documents that `FeatureRecord` will be re-exported from `sdi.parsing` in M02. When that happens, `tests/conftest.py`, `tests/unit/test_snapshot_model.py`, and `tests/unit/test_storage.py` all import from `sdi.snapshot.model` and will need their import lines updated.
- [2026-04-10 | "M01"] `src/sdi/config.py:_DEFAULT_EXCLUDE` — Defined as a `list` (mutable), and `CoreConfig.exclude` defaults via `field(default_factory=lambda: list(_DEFAULT_EXCLUDE))`. The extra `list()` copy in the factory is correct but the underlying `_DEFAULT_EXCLUDE` could be a `tuple` or `frozenset` to make the immutability intent clearer.

## Resolved
