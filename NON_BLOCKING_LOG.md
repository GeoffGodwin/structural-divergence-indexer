# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in REVIEWER_REPORT.md.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-10 | "M01"] `tests/unit/test_storage.py:96,101` — `import re` and `import json` appear inside test method bodies; PEP 8 requires imports at the top of the file. Move both to the module-level import block.
- [ ] [2026-04-10 | "M01"] `tests/conftest.py:9` and `tests/unit/test_snapshot_model.py:9` — `FeatureRecord` is imported from `sdi.snapshot.model`. Per CLAUDE.md, the canonical home is `sdi.parsing`. The comment in `model.py` explains this is intentional for M01, but when M02 moves the definition these import sites will need updating.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
