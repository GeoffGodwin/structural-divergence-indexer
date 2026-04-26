# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in ${REVIEWER_REPORT_FILE}.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-26 | "M15"] [tests/integration/test_shell_pipeline.py:38,58] Security agent (LOW/fixable): `dest.chmod(... | S_IXUSR | S_IXGRP | S_IXOTH)` silently grants group- and world-execute beyond source intent. Both the `shell_project` fixture and the `_make_shell_project` helper contain the same pattern. Fix: replace with `shutil.copymode(src, dest)` or set only `S_IXUSR` to mirror the source bit faithfully. Test dirs are ephemeral tmp_path so impact is negligible, but the pattern should not become a template for future fixtures.
- [x] [2026-04-26 | "M15"] [src/sdi/graph/builder.py] Shell constants (`_SHELL_LANGS`, `_SHELL_EXTENSIONS_FOR_FALLBACK`, `_KNOWN_SHELL_EXTS`) and `_resolve_shell_import` currently live in builder.py rather than a dedicated `_shell_resolver.py` sibling of `_js_ts_resolver.py`. At 299 lines builder.py is just under the ceiling; a future shell expansion would push it over. Not a blocker today.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
