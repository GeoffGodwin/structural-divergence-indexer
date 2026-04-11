# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in REVIEWER_REPORT.md.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-10 | "M03"] Security agent LOW finding (outside M03 scope): `src/sdi/parsing/discovery.py:50` still passes `"gitwildmatch"` to `pathspec.PathSpec.from_lines()` in the empty-spec branch. Line 52 was fixed to `"gitignore"` but line 50 was missed. Low-risk but will emit deprecation warnings when no `.gitignore` is present. Should be fixed independently.
- [ ] [2026-04-10 | "M03"] Go pattern detection at `go.py:197` uses `"err" in _node_text(cond)` substring match — will match any `if` condition whose text contains "err" (e.g. `if stderr != ""`, `if locker != nil`). Accepted heuristic per SDI's measurement-not-judgment principle, but worth documenting in-code as an acknowledged limitation.
- [ ] [2026-04-10 | "M03"] Rust match pattern at `rust.py:199` matches `"None"` as a substring — could trigger on enum variants like `NoneType` or string literals. Same caveat: accepted approximation; worth a comment.
- [ ] [2026-04-10 | "M01"] `tests/unit/test_storage.py:96,101` — `import re` and `import json` appear inside test method bodies; PEP 8 requires imports at the top of the file. Move both to the module-level import block.
- [ ] [2026-04-10 | "M01"] `tests/conftest.py:9` and `tests/unit/test_snapshot_model.py:9` — `FeatureRecord` is imported from `sdi.snapshot.model`. Per CLAUDE.md, the canonical home is `sdi.parsing`. The comment in `model.py` explains this is intentional for M01, but when M02 moves the definition these import sites will need updating.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
