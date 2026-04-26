# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in ${REVIEWER_REPORT_FILE}.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-26 | "M18"] `tests/integration/test_validation_real_repos.py:55-58` — `if init_result.exit_code not in (0,): pass` is a dead-code no-op. The comment explains the rationale but the branch body does nothing; simplify to just a comment or remove the conditional entirely.
- [ ] [2026-04-26 | "M18"] `docs/validation.md:93-100` — The re-capture instructions contain a placeholder Python snippet that is incomplete and non-functional (`# ... (see test_validation_real_repos.py for the full flow)`). Replace with working prose or a working script; as written it tells the reader to look at the test file, which is circular.
- [ ] [2026-04-26 | "M18"] `CHANGELOG.md:8-9` — `## [Unreleased]` and `## [0.14.5]` are on consecutive lines with no blank line between them; minor inconsistency with the rest of the file's formatting.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
