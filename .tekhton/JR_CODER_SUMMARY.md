# Jr Coder Summary — 2026-04-26

## Architect Plan: Cleanup Tasks

Completed all items from `.tekhton/ARCHITECT_PLAN.md` assigned to jr coder.

---

## Dead Code Removal

### Removed Private Symbol Re-exports from `src/sdi/graph/builder.py`

Removed 5 dead re-export lines that were added for backward compatibility when `_js_ts_resolver.py` was extracted in M15:
- `_JS_TS_EXTS` (line 31)
- `_expand_alias_candidates` (line 34)
- `_match_alias` (line 37)
- `_strip_jsonc` (line 40)
- `_try_extensions_and_index` (line 41)

**Change:** Removed all 5 `# noqa: F401` re-export lines from the import block. The module now imports only the symbols it directly uses:
- `_JS_TS_LANGS`
- `_build_js_path_set`
- `_is_js_ts_file`
- `_load_ts_path_aliases`
- `_normalize_js_path`
- `_resolve_js_import`

### Updated Test Imports in `tests/unit/test_graph_builder.py`

Moved three functions that were being imported from `builder` to direct imports from `_js_ts_resolver`:
- `_match_alias`
- `_strip_jsonc`
- `_try_extensions_and_index`

These are the only test-caller sites for these functions; zero other callers import them from `builder`.

**Change:** Reorganized imports into two blocks:
1. From `sdi.graph._js_ts_resolver`: the three functions now imported directly from their source
2. From `sdi.graph.builder`: remaining functions (`_build_module_map`, `_file_path_to_module_key`, `_load_ts_path_aliases`, `_resolve_import`, `_resolve_js_import`, `build_dependency_graph`)

---

## Verification

✓ **ruff check**: All checks passed on both modified files  
✓ **mypy**: No type errors in either file  
✓ **pytest**: All 88 unit tests in `test_graph_builder.py` pass  

---

## Notes

- **Staleness Fixes**: No changes needed (section marked "None" in plan)
- **Naming Normalization**: No changes needed (no items listed)
- **Simplification items skipped**: Per instructions, simplification items were not addressed (e.g., fixture consolidation, helper deduplication)
- **Design Doc Observations routed to human**: Not addressed by jr coder (docstring notes and CLAUDE.md updates for `category_languages` asymmetry)
