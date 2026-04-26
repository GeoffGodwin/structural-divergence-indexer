## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `src/sdi/snapshot/_lang_delta.py:14` — `build_file_language_map(feature_records: list)` uses bare `list` without type parameter; CLAUDE.md requires type hints on all public function signatures. Should be `list[FeatureRecord]` (importable via TYPE_CHECKING).
- `src/sdi/snapshot/_lang_delta.py:38,72` — `catalog_dict: dict` in both per-language functions should be `dict[str, Any]` for consistency with the rest of the codebase.
- `src/sdi/snapshot/_lang_delta.py:72` — `per_language_convention_drift` counts deduplicated file paths (one per file per shape after `ShapeStats.to_dict()` runs `sorted(set(...))`) rather than raw instance counts. This means a shape appearing 5× in the same file contributes the same weight as one appearing once. The global `_catalog_convention_drift` uses `instance_count` — this asymmetry is undocumented in the docstring.
- `src/sdi/cli/show_cmd.py` / `src/sdi/cli/diff_cmd.py` — `convention_drift_by_language` and `convention_drift_by_language_delta` are computed and stored but never rendered in text mode. Only `pattern_entropy_by_language` gets a UI section. If the milestone spec intended both to appear, this is a gap; if only entropy was in scope, it should be noted in docs/CHANGELOG.

## Coverage Gaps
- No integration test for `sdi diff` text output containing the per-language section — only `sdi show` is exercised in `test_cli_per_language.py`.
- `convention_drift_by_language` and its delta are untested via CLI output paths; coverage exists only at the unit level through `test_delta_per_language.py`.

## Drift Observations
- `src/sdi/patterns/catalog.py:131-141` — `category_languages` is computed from the live registry at `to_dict()` time but silently dropped by `from_dict()`. The field is informational (snapshot consumers can read it), but round-tripping through `from_dict → to_dict` regenerates it from the current registry, not from what was stored. If a future version removes a category from the registry, that category's `category_languages` entry vanishes from re-serialized old snapshots. This is low-risk today but worth documenting as a known behavior.
- `tests/unit/_delta_helpers.py:61-87` — `catalog_with_files` produces raw dicts with `[fp] * cnt` file_paths (potentially duplicated), while production data arriving at `per_language_convention_drift` has already passed through `ShapeStats.to_dict()`'s `sorted(set(...))` deduplication. The numeric assertions in `test_python_drift_uses_python_canonical` (e.g., `1/3`) rely on the duplicated form and would differ under production-equivalent data (`1/2`). The tests validate logic correctly for their input, but they do not exercise the post-dedup (production-equivalent) code path.
