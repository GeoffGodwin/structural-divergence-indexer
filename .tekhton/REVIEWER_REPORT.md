# Reviewer Report — M17 (patterns.scope_exclude config key)
Review cycle: 1 of 4

## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `_config_scope.py:16,37` — `_validate_scope_exclude(patterns: list)` and `_warn_unknown_keys(data: dict)` use bare collection types without parameters. The "type hints on all public function signatures" rule technically covers only public functions, but using `list[Any]` / `dict[str, Any]` would be more consistent with the rest of the codebase.
- `pyproject.toml` version is still `0.14.3` with M17 shipped. Milestone versioning bump is a human decision; flagging for awareness only.

## Coverage Gaps
- No test for the 100%-exclusion edge case (scope_exclude matches all files). The catalog result in this case is untested — all categories would have empty shapes, but no assertion currently verifies this.
- The `.replace("\\", "/")` Windows-path normalization branch in `catalog.py:201` is not exercised by any test. Platform-specific and hard to run in Linux CI, but the code path is untested.

## ACP Verdicts
- ACP: Extraction of `_warn_unknown_keys` + `_validate_scope_exclude` to `src/sdi/_config_scope.py` — **ACCEPT** — The 300-line ceiling is a hard rule per `reviewer.md`; config.py sits at 296 lines after the extraction (would have been ~320 without it). The extracted module has no SDI module dependencies, so no circular imports are introduced and the "leaf dependency" spirit of config.py is preserved. The leading `_` name correctly signals it is private to config.py.

## Drift Observations
- `catalog.py:17` — `import pathspec` is an unconditional top-level import that runs on every import of the module, even when `scope_exclude` is empty (the common case). Not a practical concern given pathspec is a declared lightweight dependency, but if startup time becomes a target this could be deferred to the `if scope_excl:` branch.
- `src/sdi/_config_scope.py` lives at the package root rather than in a `config/` sub-package. Fine today (single helper module), but if config.py needs further decomposition in future milestones there is no designated home for additional helpers.
