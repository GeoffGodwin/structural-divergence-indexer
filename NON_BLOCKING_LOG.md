# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in ${REVIEWER_REPORT_FILE}.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-26 | "M16"] `src/sdi/snapshot/_lang_delta.py:14` — `build_file_language_map(feature_records: list)` uses bare `list` without type parameter; CLAUDE.md requires type hints on all public function signatures. Should be `list[FeatureRecord]` (importable via TYPE_CHECKING).
- [ ] [2026-04-26 | "M16"] `src/sdi/snapshot/_lang_delta.py:38,72` — `catalog_dict: dict` in both per-language functions should be `dict[str, Any]` for consistency with the rest of the codebase.
- [ ] [2026-04-26 | "M16"] `src/sdi/snapshot/_lang_delta.py:72` — `per_language_convention_drift` counts deduplicated file paths (one per file per shape after `ShapeStats.to_dict()` runs `sorted(set(...))`) rather than raw instance counts. This means a shape appearing 5× in the same file contributes the same weight as one appearing once. The global `_catalog_convention_drift` uses `instance_count` — this asymmetry is undocumented in the docstring.
- [x] [2026-04-26 | "M16"] `src/sdi/cli/show_cmd.py` / `src/sdi/cli/diff_cmd.py` — `convention_drift_by_language` and `convention_drift_by_language_delta` are computed and stored but never rendered in text mode. Only `pattern_entropy_by_language` gets a UI section. If the milestone spec intended both to appear, this is a gap; if only entropy was in scope, it should be noted in docs/CHANGELOG.
- [ ] [2026-04-26 | "M15"] [tests/integration/test_shell_pipeline.py:38,58] Security agent (LOW/fixable): `dest.chmod(... | S_IXUSR | S_IXGRP | S_IXOTH)` silently grants group- and world-execute beyond source intent. Both the `shell_project` fixture and the `_make_shell_project` helper contain the same pattern. Fix: replace with `shutil.copymode(src, dest)` or set only `S_IXUSR` to mirror the source bit faithfully. Test dirs are ephemeral tmp_path so impact is negligible, but the pattern should not become a template for future fixtures.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
