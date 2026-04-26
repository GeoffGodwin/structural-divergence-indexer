## Test Audit Report

### Audit Summary
Tests audited: 2 files, 22 test functions
(tests/unit/test_js_ts_resolver.py: 19 functions; tests/integration/test_validation_real_repos.py: 3 functions)
Verdict: PASS

---

### Findings

#### EXERCISE: Meta-test asserts a locally-created marker, not the real function decorators
- File: tests/integration/test_validation_real_repos.py:205
- Issue: `test_real_repo_harness_skips_without_env_vars` constructs fresh
  `pytest.mark.skipif` objects with `not _TEKHTON_PATH` / `not _BIFL_PATH` and
  then asserts `tekhton_marker.args[0] is True`. Because the test body only runs
  when both env vars are absent, `not _TEKHTON_PATH` is definitionally `True`,
  making the assertion equivalent to `assert True is True` in every run. More
  importantly, the test does not inspect the actual `@pytest.mark.skipif`
  decorators on `test_tekhton_real_repo_invariants` and
  `test_bifl_tracker_real_repo_invariants` — so a mistake in those real decorators
  (e.g. an inverted condition) would not be caught.
- Severity: MEDIUM
- Action: Replace the local-marker construction with introspection of the real
  function markers via `test_tekhton_real_repo_invariants.pytestmark` and
  `test_bifl_tracker_real_repo_invariants.pytestmark`, then assert `marker.args[0]`
  on those objects. Alternatively, drop the assertions entirely and leave only the
  env-var guard with a comment, accepting that skip behaviour is verified by
  pytest's own collection logic.

#### COVERAGE: JSONC fallback path in `_load_ts_path_aliases` has no test
- File: tests/unit/test_js_ts_resolver.py (missing test)
- Issue: The M18 fix wraps `json.loads(text)` in a try/except and falls back to
  `json.loads(_strip_jsonc(text))` when the plain parse fails. The regression test
  (`test_at_wildcard_not_corrupted_when_later_string_contains_block_comment_end`)
  only exercises the plain-JSON path. No test feeds a tsconfig.json with real JSONC
  line comments to verify (a) that the fallback succeeds, and (b) that the alias
  is not corrupted when `_strip_jsonc` is actually invoked.
- Severity: LOW
- Action: Add a test in `TestLoadTsPathAliasesM18Regression` (or a new class) that
  writes a tsconfig.json with a JSONC `// …` comment plus the `@/*` alias, then
  asserts `_load_ts_path_aliases` returns the correct tuple. This closes the gap
  for the fallback branch.

#### COVERAGE: No test for absent tsconfig.json / jsconfig.json
- File: tests/unit/test_js_ts_resolver.py (missing test)
- Issue: `_load_ts_path_aliases` is expected to return an empty list when neither
  `tsconfig.json` nor `jsconfig.json` is present. This is the dominant code path
  for non-TypeScript projects and is untested.
- Severity: LOW
- Action: Add `test_returns_empty_list_when_no_config_present(tmp_path)` that calls
  `_load_ts_path_aliases` on an empty directory and asserts `== []`.

---

### Verified Clean (no findings)

**1. Assertion Honesty — PASS**
Every assertion in `test_js_ts_resolver.py` is traceable to implementation logic.
The M18 regression assertion `aliases == [("@/*", ["src/*"])]` derives from
`posixpath.normpath(posixpath.join(".", "./src/*"))` → `"src/*"` (implementation
line 96–97 in `_js_ts_resolver.py`). No hard-coded magic values.

**2. Edge Case Coverage — PASS**
`TestIsJsTsFile` covers happy path, non-JS/TS, and case-sensitivity.
`TestNormalizeJsPath` covers empty string, multiple `./` prefixes, backslashes,
and unchanged paths. `TestBuildJsPathSet` covers empty input, mixed extensions.
`TestExpandAliasCandidates` covers no-match, empty alias list, wildcard expansion,
exact match, multiple targets, first-match semantics, and prefix-skip ordering.

**3. Implementation Exercise — PASS**
All 19 test functions in `test_js_ts_resolver.py` import and call real private
functions with zero mocking. The regression test uses `tmp_path` to create a real
`tsconfig.json` on disk and exercises the full file-I/O path of
`_load_ts_path_aliases`. The integration tests run the real CLI via `CliRunner`.

**4. Test Weakening — PASS**
`test_js_ts_resolver.py` is a new file; no existing tests were modified. The
coder's change to `test_validation_real_repos.py` (`kwargs["condition"]` →
`args[0]`) corrected a `KeyError`-raising assertion — this is a fix, not a
weakening. The tester's addition of `warnings.warn` in `_run_snapshot` is additive
only (a helper function change, no assertion removed).

**5. Test Naming — PASS**
All 22 test names encode both the scenario and the expected outcome. Examples:
`test_at_wildcard_not_corrupted_when_later_string_contains_block_comment_end`,
`test_first_matching_alias_is_used`, `test_real_repo_harness_skips_without_env_vars`.
No opaque names.

**6. Scope Alignment — PASS**
All imports resolve against the current source:
- `sdi.graph._js_ts_resolver`: module present; all five imported private functions
  (`_is_js_ts_file`, `_normalize_js_path`, `_build_js_path_set`,
  `_expand_alias_candidates`, `_load_ts_path_aliases`) are defined in that module.
- `tests.conftest.run_sdi`: present at conftest.py:199.
No references to deleted modules or renamed symbols. The deleted files
(`.tekhton/JR_CODER_SUMMARY.md`, `.tekhton/test_dedup.fingerprint`) are not
referenced in any audited test file.

**7. Test Isolation — PASS**
`test_js_ts_resolver.py` uses only in-memory data and pytest's `tmp_path`.
`test_validation_real_repos.py` real-repo tests are gated behind env-var `skipif`
markers; the module docstring explicitly documents that those tests write `.sdi/`
state to external repos as intentional dogfooding behaviour. The meta-test
`test_real_repo_harness_skips_without_env_vars` is purely in-memory and reads no
project files or pipeline artifacts.
