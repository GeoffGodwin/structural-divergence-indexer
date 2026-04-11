# Jr Coder Summary — Architect Remediation (2026-04-11)

## What Was Fixed

### Staleness Fixes
- **src/sdi/snapshot/model.py (lines 4-5):** Updated forward-tense comment referencing M02 milestone. Changed "It will also be re-exported from sdi.parsing in M02" to "Also re-exported as `sdi.parsing.FeatureRecord` for external callers" (accurate, present tense).

- **src/sdi/graph/builder.py (_file_path_to_module_key docstring):** Added documentation of the assumption that `src/` is a build-layout prefix with no corresponding importable package. Clarified behavior for hypothetical projects with a real top-level package named `src`.

### Naming Normalization — Test File Imports
Changed seven test files to import `FeatureRecord` from the canonical public path `sdi.parsing` instead of the internal path `sdi.snapshot.model`:
- **tests/unit/test_go_adapter.py** (line 10)
- **tests/unit/test_rust_adapter.py** (line 10)
- **tests/unit/test_java_adapter.py** (line 10)
- **tests/unit/test_python_adapter.py** (line 17)
- **tests/unit/test_typescript_adapter.py** (line 11)
- **tests/unit/test_javascript_adapter.py** (line 10)
- **tests/unit/test_conftest_fixtures.py** (line 12)

### Naming Normalization — Type Annotations
- **src/sdi/graph/metrics.py (line 85):** Narrowed return type annotation of `compute_graph_metrics()` from bare `dict` to `dict[str, Any]`. Added `from typing import Any` import.

- **src/sdi/graph/builder.py (line 208):** Narrowed variable annotation `metadata` from bare `dict` to `dict[str, int]` (values are always `unresolved_count` and `self_import_count`, both integers).

### Naming Normalization — Single-Element Tuple
- **src/sdi/parsing/go.py (line 130):** Replaced `elif node.type in ("method_declaration",):` with `elif node.type == "method_declaration":`. The single-element tuple form was semantically misleading.

## Files Modified

1. src/sdi/snapshot/model.py
2. src/sdi/graph/builder.py
3. src/sdi/graph/metrics.py
4. tests/unit/test_go_adapter.py
5. tests/unit/test_rust_adapter.py
6. tests/unit/test_java_adapter.py
7. tests/unit/test_python_adapter.py
8. tests/unit/test_typescript_adapter.py
9. tests/unit/test_javascript_adapter.py
10. tests/unit/test_conftest_fixtures.py
11. src/sdi/parsing/go.py

## Notes

- All changes are mechanical and non-functional — no behavior altered, only documentation and type clarity improved.
- The note about the `src.` prefix assumption in `_file_path_to_module_key` documents existing behavior; no code logic was changed.
- Adapter source files (go.py, rust.py, java.py, etc.) correctly continue to import `FeatureRecord` directly from `sdi.snapshot.model` since they are internal to the parsing package.
- No items from Simplification or Design Doc Observations sections were addressed (those route to senior coder and human respectively).
