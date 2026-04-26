# Drift Log

## Metadata
- Last audit: 2026-04-26
- Runs since audit: 2

## Unresolved Observations
- [2026-04-26 | "M18"] `src/sdi/graph/_js_ts_resolver.py:44-56` — `_strip_jsonc` still has the known-bad case: a tsconfig.json with JSONC block comments *and* `@/*`-style path aliases together will corrupt the alias section when the block-comment regex spans from `@/*` to a later `*/`. The fix (try plain JSON first) eliminates the failure for the common case (no JSONC comments), and the docstring documents the residual limitation. This is not a regression from M18 but is worth a follow-up if tsconfig-with-comments + `@/*` becomes a common user scenario.
- [2026-04-26 | "M17"] `catalog.py:17` — `import pathspec` is an unconditional top-level import that runs on every import of the module, even when `scope_exclude` is empty (the common case). Not a practical concern given pathspec is a declared lightweight dependency, but if startup time becomes a target this could be deferred to the `if scope_excl:` branch.
- [2026-04-26 | "M17"] `src/sdi/_config_scope.py` lives at the package root rather than in a `config/` sub-package. Fine today (single helper module), but if config.py needs further decomposition in future milestones there is no designated home for additional helpers.
- [2026-04-26 | "architect audit"] **[M10] `init_cmd.py:232-233` deferred imports in `_infer_boundaries_from_snapshot`** — The imports (`list_snapshots`, `read_snapshot`, `partition_to_proposed_yaml`) are intentionally deferred inside a best-effort helper that catches all exceptions and returns `None` on failure. This pattern is correct: hoisting these imports to module level would cause `sdi init` to fail on startup if `sdi.snapshot.storage` or `sdi.detection.boundaries` have import-time errors, rather than gracefully degrading. The style inconsistency with the rest of the module is real but not a structural risk. Leave in drift log for the next style-pass cycle; do not address in this plan.

## Resolved
