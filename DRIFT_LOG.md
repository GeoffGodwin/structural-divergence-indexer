# Drift Log

## Metadata
- Last audit: 2026-04-26
- Runs since audit: 2

## Unresolved Observations

None.

## Resolved
- [RESOLVED 2026-04-26] `CHANGELOG.md:18-19` — Pre-existing: no blank line between the `- [x]` checkbox entry (which looks misplaced inside `[0.14.5]`) and the `## [0.14.4]` heading. Inconsistent with the rest of the file. Not introduced by this commit but worth a cleanup pass.
- [RESOLVED 2026-04-26] `src/sdi/graph/_js_ts_resolver.py:44-56` — `_strip_jsonc` still has the known-bad case: a tsconfig.json with JSONC block comments *and* `@/*`-style path aliases together will corrupt the alias section when the block-comment regex spans from `@/*` to a later `*/`. The fix (try plain JSON first) eliminates the failure for the common case (no JSONC comments), and the docstring documents the residual limitation. This is not a regression from M18 but is worth a follow-up if tsconfig-with-comments + `@/*` becomes a common user scenario.
- [RESOLVED 2026-04-26] `catalog.py:17` — `import pathspec` is an unconditional top-level import that runs on every import of the module, even when `scope_exclude` is empty (the common case). Not a practical concern given pathspec is a declared lightweight dependency, but if startup time becomes a target this could be deferred to the `if scope_excl:` branch.
- [RESOLVED 2026-04-26] `src/sdi/_config_scope.py` lives at the package root rather than in a `config/` sub-package. Fine today (single helper module), but if config.py needs further decomposition in future milestones there is no designated home for additional helpers.
- [RESOLVED 2026-04-26] **[M10] `init_cmd.py:232-233` deferred imports in `_infer_boundaries_from_snapshot`** — The imports (`list_snapshots`, `read_snapshot`, `partition_to_proposed_yaml`) are intentionally deferred inside a best-effort helper that catches all exceptions and returns `None` on failure. This pattern is correct: hoisting these imports to module level would cause `sdi init` to fail on startup if `sdi.snapshot.storage` or `sdi.detection.boundaries` have import-time errors, rather than gracefully degrading. The style inconsistency with the rest of the module is real but not a structural risk. Leave in drift log for the next style-pass cycle; do not address in this plan.
- [RESOLVED 2026-04-26] **`_js_ts_resolver.py:44-56` `_strip_jsonc` residual JSONC+`@/*` bug (audit defer)** — No user reports confirm this edge case is common. The M18 fix (try plain JSON first) covers the common case; the docstring in `_strip_jsonc` documents the residual limitation. Decision: DEFERRED — revisit if and when user reports surface confirming the tsconfig-with-comments + `@/*` scenario is widespread.
- [RESOLVED 2026-04-26] **`catalog.py:17` unconditional `import pathspec` (audit defer)** — Pathspec is a declared lightweight dependency with negligible import cost. Deferring to the `if scope_excl:` branch is a speculative micro-optimization with no measurable startup-time benefit at this scale. Decision: DEFERRED — revisit if startup profiling identifies import cost as a meaningful contributor.
- [RESOLVED 2026-04-26] **`src/sdi/_config_scope.py` at package root (audit defer)** — Single helper module at the package root poses no structural risk. Concern is prospective only. Decision: DEFERRED — revisit if a second config helper is added that warrants a `config/` sub-package.
- [RESOLVED 2026-04-26] **`init_cmd.py:232-233` deferred imports style inconsistency (style-pass)** — The deferred-import pattern inside `_infer_boundaries_from_snapshot` is intentionally correct for graceful degradation: hoisting to module level would cause startup failure if `sdi.snapshot.storage` or `sdi.detection.boundaries` have import-time errors. The style inconsistency with the rest of the module is accepted as the cost of correctness. Decision: ACCEPTED — pattern is correct; no change warranted.
- [RESOLVED 2026-04-26] **`CHANGELOG.md:8-9` missing blank line between `## [Unreleased]` and `## [0.14.6]`** — Pre-existing Keep a Changelog formatting inconsistency. Fixed: blank line added between the two headings.
- [RESOLVED 2026-04-26] **`CHANGELOG.md:11-12` removal documented under `### Added` in `[0.14.6]`** — Dead-code removal is a structural change, not an addition. Fixed: section header changed from `### Added` to `### Changed`.
- [RESOLVED 2026-04-26] **`CHANGELOG.md:24-28` duplicate `### Added` sections in `[0.14.4]`** — Keep a Changelog format requires each type heading to appear at most once per release. Fixed: the two `### Added` sections merged into one.
