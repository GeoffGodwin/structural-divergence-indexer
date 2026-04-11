# Coder Summary
## Status: COMPLETE

## What Was Implemented

**Stage 4 of the SDI pipeline — Pattern Fingerprinting and Catalog.**

- **`src/sdi/patterns/fingerprint.py`** — `PatternFingerprint` frozen dataclass (equality/hashing based on `structural_hash` only). `compute_structural_hash(descriptor, min_nodes)` normalizes AST descriptor dicts: identifier types → `"_ID_"`, literal types → `"_STR_"` / `"_INT_"` / etc.; hashes with SHA-256[:16]. `fingerprint_from_instance(instance, min_nodes)` wraps pre-computed `ast_hash` values from FeatureRecord.pattern_instances; filters by `node_count` if present.

- **`src/sdi/patterns/categories.py`** — `CategoryDefinition` dataclass. `CATEGORY_NAMES` list of all seven built-in categories. Tree-sitter query strings for Python keyed per category. `get_category()`, `get_all_categories()`, `is_registered_category()` — unknown names return `None`, never raise.

- **`src/sdi/patterns/catalog.py`** — `ShapeStats`, `CategoryStats`, `PatternCatalog` dataclasses with `to_dict()`/`from_dict()` JSON round-trip support. `CategoryStats.entropy` = `len(shapes)`, `canonical_hash` = highest instance count shape. `build_pattern_catalog(records, config, prev_catalog, partition)`: collects instances, applies `min_pattern_nodes` filter, computes velocity (null on first snapshot, integer delta on subsequent), boundary spread (null without partition, distinct cluster count with). All seven built-in categories always present, even with zero instances.

- **`src/sdi/patterns/__init__.py`** — Public API: `build_pattern_catalog`, `PatternCatalog`, `PatternFingerprint`, `CategoryStats`, `ShapeStats`, `compute_structural_hash`.

- **`tests/fixtures/high-entropy/`** — 10 Python files: `error_bare.py`, `error_single.py`, `error_multi.py`, `error_finally.py`, `error_else.py` (5 distinct error handling structures), `data_orm.py`, `data_cursor.py`, `data_dict.py` (3 data access styles), `logging_module.py`, `logging_instance.py` (2 logging styles), `mixed_patterns.py`.

- **`tests/unit/test_fingerprint.py`** — 22 tests covering structural hash equality/inequality, identifier stripping, literal stripping, min_nodes threshold filtering, PatternFingerprint equality, hashability, fingerprint_from_instance with/without node_count.

- **`tests/unit/test_catalog.py`** — 13 tests covering CategoryStats (entropy, canonical_hash), build_pattern_catalog grouping/counting, all-builtin-categories guarantee, empty category, min_pattern_nodes filtering, JSON round-trip.

- **`tests/unit/test_catalog_velocity_spread.py`** — 11 tests covering velocity (null first snapshot, delta, negative, new shape), boundary spread (null without partition, cross-cluster count, single-cluster), high-entropy fixture assertions (≥4 error_handling, ≥3 data_access, ≥2 logging).

- **`tests/unit/test_categories.py`** — 9 tests covering all seven categories registered, name resolution, unknown returns None, descriptions, Python queries, get_all_categories copy semantics.

- **`tests/conftest.py`** — Added `sample_pattern_fingerprint`, `sample_pattern_catalog`, `sample_community_result` shared fixtures.

## Root Cause (bugs only)
N/A — feature implementation.

## Files Modified
- `src/sdi/patterns/__init__.py` (NEW)
- `src/sdi/patterns/fingerprint.py` (NEW)
- `src/sdi/patterns/categories.py` (NEW)
- `src/sdi/patterns/catalog.py` (NEW)
- `tests/unit/test_fingerprint.py` (NEW)
- `tests/unit/test_catalog.py` (NEW)
- `tests/unit/test_catalog_velocity_spread.py` (NEW)
- `tests/unit/test_categories.py` (NEW)
- `tests/fixtures/high-entropy/error_bare.py` (NEW)
- `tests/fixtures/high-entropy/error_single.py` (NEW)
- `tests/fixtures/high-entropy/error_multi.py` (NEW)
- `tests/fixtures/high-entropy/error_finally.py` (NEW)
- `tests/fixtures/high-entropy/error_else.py` (NEW)
- `tests/fixtures/high-entropy/data_orm.py` (NEW)
- `tests/fixtures/high-entropy/data_cursor.py` (NEW)
- `tests/fixtures/high-entropy/data_dict.py` (NEW)
- `tests/fixtures/high-entropy/logging_module.py` (NEW)
- `tests/fixtures/high-entropy/logging_instance.py` (NEW)
- `tests/fixtures/high-entropy/mixed_patterns.py` (NEW)
- `tests/conftest.py` (MODIFIED — added 3 shared fixtures)

## Human Notes Status
No Human Notes section present in this milestone.

## Observed Issues (out of scope)
- `src/sdi/detection/_partition_cache.py:45` — `_read_cache()` calls `.get()` on parsed JSON data without first checking `isinstance(data, dict)`. A top-level JSON array causes `AttributeError`. Pre-existing bug, confirmed failing before M06. Test: `tests/unit/test_leiden_internals.py::test_read_cache_toplevel_array_returns_none`.
