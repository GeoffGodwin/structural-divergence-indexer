# Coder Summary
## Status: COMPLETE

## What Was Implemented

- **`src/sdi/patterns/categories.py`**: Added `languages: frozenset[str]` field to `CategoryDefinition`. Populated all seven built-in categories with their applicable-language sets. Added `applicable_languages(name)` function returning `None` for unknown names. Added module docstring documenting the empty-means-all-languages convention.

- **`src/sdi/patterns/catalog.py`**: Added language-scope filtering in `build_pattern_catalog` — fingerprints whose category has a non-empty `languages` set are silently dropped when `record.language` is not in that set. Added `category_languages: dict[str, list[str]]` to `PatternCatalog.to_dict()` with sorted lists for deterministic output.

- **`src/sdi/snapshot/model.py`**: Added four new optional fields to `DivergenceSummary`: `pattern_entropy_by_language`, `pattern_entropy_by_language_delta`, `convention_drift_by_language`, `convention_drift_by_language_delta`. Updated `to_dict` and `from_dict` for round-trip. Bumped `SNAPSHOT_VERSION` from `"0.1.0"` to `"0.2.0"`.

- **`src/sdi/snapshot/_lang_delta.py`** (NEW): Per-language delta helpers: `build_file_language_map`, `per_language_pattern_entropy`, `per_language_convention_drift`. Uses per-language canonicals for drift computation to prevent cross-language baseline contamination.

- **`src/sdi/snapshot/delta.py`**: Updated `compute_delta` to compute per-language fields for current snapshot. When previous is `None`, all `_delta` fields are `None`. When previous is `"0.1.0"`, emits exactly one `UserWarning` and returns per-language `_delta` as `None` (aggregate delta still computed). Handles new-language-added case (previous value treated as `0.0`).

- **`src/sdi/snapshot/assembly.py`**: Already imports `compute_delta` which now includes per-language logic — no additional changes needed.

- **`src/sdi/cli/show_cmd.py`**: Renders a "Per-Language Pattern Entropy" section in text mode when `pattern_entropy_by_language` is present; sorted by entropy descending with delta column.

- **`src/sdi/cli/diff_cmd.py`**: Same per-language section in `_print_diff_text`.

- **`tests/unit/test_categories.py`**: Added M16 tests: `applicable_languages()` per category, unknown name returns `None`, frozenset type assertion, all built-in categories have non-empty languages, shell categories have no shell ts_query.

- **`tests/unit/test_catalog.py`**: Added M16 tests: `class_hierarchy` filtered from shell records, `error_handling` accepted from shell records, `category_languages` in `to_dict`, round-trip.

- **`tests/unit/_delta_helpers.py`** (NEW): Shared test helpers (`make_snap`, `catalog`, `catalog_with_files`, `fake_record`, `metrics`, `partition`) shared between `test_delta.py` and `test_delta_per_language.py`.

- **`tests/unit/test_delta_per_language.py`** (NEW): Tests for `per_language_pattern_entropy`, `per_language_convention_drift`, and `compute_delta` per-language fields including `0.1.0` backward compat warning, new-language-added delta, determinism.

- **`tests/unit/test_snapshot_model.py`**: Added M16 tests: per-language fields default to `None`, round-trip with values, `from_dict` with old `0.1.0` dict, `Snapshot.from_dict` handles missing per-language keys.

- **`tests/integration/test_cli_per_language.py`** (NEW): Asserts `sdi show --format json` includes per-language keys; text mode renders "Per-Language Pattern Entropy" section.

- **`tests/integration/test_pipeline_per_language.py`** (NEW): Pipeline tests on multi-language and shell-heavy fixtures asserting per-language entropy presence and determinism.

- **`README.md`**: Added one-paragraph note in the "what SDI measures" section about per-language reporting.

- **`CHANGELOG.md`**: Added "Unreleased" entry documenting the four new fields, `applicable_languages`, and schema version bump.

## Root Cause (bugs only)
N/A — feature milestone

## Files Modified

- `src/sdi/patterns/categories.py` — added languages field, applicable_languages(), module docstring
- `src/sdi/patterns/catalog.py` — language filtering, category_languages in to_dict
- `src/sdi/snapshot/model.py` — four new DivergenceSummary fields, SNAPSHOT_VERSION 0.2.0
- `src/sdi/snapshot/delta.py` — per-language computation in compute_delta
- `src/sdi/snapshot/_lang_delta.py` (NEW) — per-language helper functions
- `src/sdi/cli/show_cmd.py` — per-language section in text output
- `src/sdi/cli/diff_cmd.py` — per-language section in text output
- `tests/unit/test_categories.py` — M16 language-scope tests
- `tests/unit/test_catalog.py` — M16 filtering and category_languages tests
- `tests/unit/test_delta.py` — imports updated to use _delta_helpers
- `tests/unit/test_snapshot_model.py` — M16 per-language field tests
- `tests/unit/_delta_helpers.py` (NEW) — shared snapshot/catalog factory helpers
- `tests/unit/test_delta_per_language.py` (NEW) — M16 per-language delta tests
- `tests/integration/test_cli_per_language.py` (NEW) — CLI output assertions
- `tests/integration/test_pipeline_per_language.py` (NEW) — pipeline assertions
- `README.md` — per-language measurement paragraph
- `CHANGELOG.md` — Unreleased entry

## Human Notes Status
No human notes section present in this milestone.

## Docs Updated
- `README.md` — added per-language paragraph after the four-dimension list
- `CHANGELOG.md` — added Unreleased entry for M16 schema changes

## Observed Issues (out of scope)
None observed.
