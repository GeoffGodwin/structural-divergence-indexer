## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- [tests/integration/test_shell_pipeline.py:38,58] Security agent (LOW/fixable): `dest.chmod(... | S_IXUSR | S_IXGRP | S_IXOTH)` silently grants group- and world-execute beyond source intent. Both the `shell_project` fixture and the `_make_shell_project` helper contain the same pattern. Fix: replace with `shutil.copymode(src, dest)` or set only `S_IXUSR` to mirror the source bit faithfully. Test dirs are ephemeral tmp_path so impact is negligible, but the pattern should not become a template for future fixtures.
- [src/sdi/graph/builder.py] Shell constants (`_SHELL_LANGS`, `_SHELL_EXTENSIONS_FOR_FALLBACK`, `_KNOWN_SHELL_EXTS`) and `_resolve_shell_import` currently live in builder.py rather than a dedicated `_shell_resolver.py` sibling of `_js_ts_resolver.py`. At 299 lines builder.py is just under the ceiling; a future shell expansion would push it over. Not a blocker today.

## Coverage Gaps
- No unit test for the `.` (dot-command) form as a `source` alias — `_extract_imports` in shell.py handles it, but `_resolve_shell_import` has no test using an import that arrived via a `.` directive rather than `source`.
- No integration test for a shell-only repo with zero `source` edges (edge_count = 0, component_count = file_count) to confirm the base case produces a valid snapshot rather than a crash.
- No test covering a shell FeatureRecord whose import string contains `$VAR` or backtick (dynamic form); the shell adapter silently skips these, but a malformed FeatureRecord with such a string should be confirmed to return None from `_resolve_shell_import` gracefully.

## ACP Verdicts
- ACP: Extract JS/TS helpers to `_js_ts_resolver.py` — ACCEPT — The extraction is warranted: builder.py was 455 lines pre-M15 and would have exceeded 300 again with shell additions. All names are re-exported for backward compatibility, the module carries a leading underscore indicating internal scope, and the public surface of `sdi.graph.builder` is unchanged. No architecture doc update required.

## Drift Observations
- [src/sdi/graph/builder.py:31-42] The `# noqa: F401 — re-exported for backward compatibility` comments on `_JS_TS_EXTS`, `_expand_alias_candidates`, `_match_alias`, `_strip_jsonc`, and `_try_extensions_and_index` suggest these private symbols were imported into test files directly. Private symbols with leading underscores are not part of the public API contract; tests importing them directly from `builder` instead of `_js_ts_resolver` create a maintenance burden. Worth auditing whether those re-exports can be dropped when the pre-M15 tests are updated.
- [tests/integration/test_shell_pipeline.py:43-59] `_make_shell_project` is a free function that duplicates the body of the `shell_project` fixture verbatim (modulo fixture_name parameter). The fixture calls the helper anyway, making the duplication one-way. Consider collapsing the fixture to just call `_make_shell_project(tmp_path, "simple-shell")` to eliminate the copy.
