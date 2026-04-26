## Test Audit Report

### Audit Summary
Tests audited: 1 file, 6 test functions
Verdict: PASS

---

### Findings

#### COVERAGE: Text-mode section suppression not exercised
- File: tests/integration/test_cli_per_language.py:156
- Issue: `test_show_text_renders_per_language_section` verifies the "Per-Language Pattern
  Entropy" section IS rendered when the field is populated. No integration test verifies
  that the section is absent — and causes no crash — when `pattern_entropy_by_language`
  is `None` (e.g., a first-snapshot or catalog-less snapshot). The same gap exists for
  `sdi diff` text mode. Both `show_cmd._format_text` and `diff_cmd._print_diff_text`
  guard on the field's truthiness; the guard is untested via the CLI path.
- Severity: LOW
- Action: Add one test each to `TestShowPerLanguageOutput` and `TestDiffPerLanguageOutput`
  that write a snapshot with no catalog/per-language fields and assert that (a) exit_code
  is 0 and (b) "Per-Language Pattern Entropy" is NOT in the output. The
  `sample_snapshot` conftest fixture (all per-language fields None) is a ready-made input.

#### COVERAGE: Redundant None guard before membership assertion
- File: tests/integration/test_cli_per_language.py:152, 193
- Issue: `assert by_lang is not None` is immediately followed by `assert "python" in
  by_lang`. If `by_lang` were `None`, the membership test already raises `TypeError`,
  making the explicit None check redundant — it provides no additional diagnostic signal
  and could be mistaken for a meaningful invariant. Same pattern at line 193.
- Severity: LOW
- Action: Remove the explicit `is not None` checks and rely on the membership assertions
  alone. No logic change required.

#### COVERAGE: Fixture uses duplicate file_path entries to simulate instance_count
- File: tests/integration/test_cli_per_language.py:61
- Issue: `_make_python_catalog_dict` constructs `shape_dominant` with
  `"file_paths": ["src/foo.py", "src/foo.py"]` (identical entries) to produce the
  appearance of `instance_count: 2`. The real pipeline deduplicates `file_paths` via
  `ShapeStats.to_dict()` (`sorted(set(...))`), so a real snapshot with two instances
  from the same file serializes to `["src/foo.py"]` with `instance_count: 2`. Because
  the test injects the raw dict directly (bypassing `PatternCatalog.to_dict()`),
  `per_language_convention_drift` counts the duplicate entry twice. The assertions
  are currently correct, but the fixture diverges from what the real pipeline produces
  and creates implicit coupling to the list-entry counting behavior.
- Severity: LOW
- Action: Restructure `_make_python_catalog_dict` so `shape_dominant` references two
  distinct file paths (e.g., `["src/foo.py", "src/baz.py"]`) with `instance_count: 2`.
  Add `"src/baz.py"` to the companion `feature_records` in `_write_diff_pair`. This
  aligns the fixture with real pipeline output and removes the dependency on duplicate
  list-entry counting.

---

### Verified Clean (no findings)

**1. Assertion Honesty — PASS**
All six assertions derive values from actual function calls, not hard-coded constants.
`assert "python" in by_lang` is valid because the snapshot is written with
`pattern_entropy_by_language={"python": 2.0, "shell": 1.0}` and `Snapshot.to_dict()`
uses `dataclasses.asdict` which round-trips all fields unchanged through `show_cmd`'s
`emit_json` path. For the diff tests, `compute_delta` recomputes per-language data from
`snap_b.feature_records` and `snap_b.pattern_catalog`; tracing through
`per_language_pattern_entropy` and `per_language_convention_drift` confirms `{"python":
2.0}` and `{"python": ~0.333}` respectively, making all `"python" in ...` assertions
sound.

**2. Implementation Exercise — PASS**
Tests use `write_snapshot` (real atomic I/O), invoke the CLI via `runner.invoke` with
`catch_exceptions=False` (no mock layer), and trigger the full `compute_delta` →
`per_language_pattern_entropy` → `per_language_convention_drift` →
`_print_diff_text`/`emit_json` stack. The per-language delta computation through
`_lang_delta.py` is directly exercised by the three diff tests.

**3. Test Weakening — PASS**
The tester's change added only new content: the `_write_diff_pair` helper and the
`TestDiffPerLanguageOutput` class (three test methods). The three pre-existing
`TestShowPerLanguageOutput` tests are unchanged. No assertion was removed or broadened.

**4. Test Naming — PASS**
All six names encode both scenario and expected outcome:
`test_show_json_includes_per_language_fields`,
`test_show_json_includes_convention_drift_by_language`,
`test_show_text_renders_per_language_section`,
`test_diff_text_renders_per_language_section`,
`test_diff_json_includes_convention_drift_by_language`,
`test_diff_json_includes_pattern_entropy_by_language`.

**5. Scope Alignment — PASS**
All imports resolve to currently existing symbols: `SNAPSHOT_VERSION`, `DivergenceSummary`,
`FeatureRecord`, `Snapshot` in `src/sdi/snapshot/model.py`; `write_snapshot` in
`src/sdi/snapshot/storage.py`; `run_sdi` in `tests/conftest.py`. The deleted file
`.tekhton/test_dedup.fingerprint` is not referenced anywhere in the test file.

**6. Test Isolation — PASS**
Both test classes use the `sdi_project_dir` fixture (function-scoped `tmp_path` with
`.git/` and `.sdi/snapshots/` pre-created). All snapshot data is written to that temp
directory. No test reads `.tekhton/`, `.claude/logs/`, pipeline logs, or any other
mutable project file. Pass/fail outcomes are independent of prior pipeline runs and
repository state.

**Delta correctness for diff tests — independently verified**
`compute_delta(snap_b, snap_a)` with snap_a (version 0.2.0, empty divergence, no catalog)
and snap_b (version 0.2.0, two Python FeatureRecords, error_handling catalog with two
shapes): both snapshots share major version "0"; the `0.1.0` backward-compat branch is
not taken; `prev_lang_entropy = {}` and `prev_lang_drift = {}` (snap_a divergence all
None). Resulting `lang_entropy_delta = {"python": 2.0}` and `lang_drift_delta =
{"python": ~0.333}` — both non-None and containing "python". The three diff assertions
(`pattern_entropy_by_language_delta is not None`, `convention_drift_by_language_delta is
not None`, `"python" in delta`) are all sound.
