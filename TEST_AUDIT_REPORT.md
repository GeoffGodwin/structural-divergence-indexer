## Test Audit Report

### Audit Summary
Tests audited: 3 files, 69 test functions  
(`test_config.py`: 29, `test_cli.py`: 20, `test_init_cmd.py`: 20)  
Verdict: CONCERNS

---

### Findings

#### COVERAGE: Gitignore test assertion is a conditional no-op
- File: tests/unit/test_init_cmd.py:204
- Issue: `test_gitignore_updated_with_sdi_cache` wraps its only meaningful assertion inside `if gitignore.exists()`. If `sdi init` silently fails to write `.gitignore` (e.g., a regression in `write_atomic`), this test passes without verifying anything. The test's stated purpose — confirming `.gitignore` is updated — becomes untestable.
- Severity: HIGH
- Action: Replace the conditional guard with an unconditional assertion. The first line should be `assert gitignore.exists(), "sdi init must create .gitignore"`, followed by the content check. `_update_gitignore` always creates the file when absent, so the guard is both unnecessary and masking.

---

#### COVERAGE: `_find_git_root` no-git-root tests have unfalsifiable conditional assertions
- File: tests/unit/test_init_cmd.py:32 and tests/unit/test_init_cmd.py:39
- Issue: Both `test_returns_none_when_no_git_root` and `test_returns_none_for_bare_tmp_with_no_git` use the pattern `if result is not None: assert (result / ".git").exists()`. Neither test ever unconditionally asserts `None`. The second test only asserts `result != child` and `result != root`, which trivially pass because neither directory contains `.git`. A bug that made `_find_git_root` return an arbitrary path with a `.git` would pass both tests. The intended behavior (return `None` when no repo exists) is never actually asserted.

  pytest's `tmp_path` creates directories under the OS temp dir (typically `/tmp/pytest-*/`), which is not inside any git repo. The conditional "CI runner inside a repo" concern in the comments is unfounded for `tmp_path`-based paths. The tests should assert `None` unconditionally.
- Severity: MEDIUM
- Action: In `test_returns_none_when_no_git_root`, replace the conditional with `assert result is None`. In `test_returns_none_for_bare_tmp_with_no_git`, replace both conditional and trivial assertions with `assert result is None`. If there is genuine concern about CI environments, use `monkeypatch` to ensure the walk terminates before the real filesystem root.

---

#### NAMING: Test name claims context verification that the test does not perform
- File: tests/unit/test_cli.py:26
- Issue: `test_format_text_stored_in_context` (docstring: "–format text wires into ctx.obj['format']") does not inspect `ctx.obj` at all. It only verifies that `--format text` is accepted without a usage error (exit_code == 1, not 2). Verifying context storage requires a different approach (e.g., a test command that echoes `ctx.obj`). The current assertion is valid but tests a different property than the name states. A reader expecting this test to catch a context-wiring regression will be misled.
- Severity: MEDIUM
- Action: Rename to `test_format_text_flag_accepted_without_usage_error` and update the docstring to match the actual assertion. If wiring into `ctx.obj` must be tested, add a separate test that invokes a helper command which reads and echoes `ctx.obj["format"]`.

---

#### COVERAGE: Verbose traceback path in `_SDIGroup` is untested
- File: tests/unit/test_cli.py:71
- Issue: `_SDIGroup.invoke` has a branch `if verbose: traceback.print_exc(file=sys.stderr)` (cli/__init__.py:26-27). The `TestSDIGroupExceptionHandler` tests never invoke the test group with a `verbose=True` context. The traceback output path is untested. This is the path a developer would rely on when debugging CI failures.
- Severity: MEDIUM
- Action: Add a test that sets `ctx.obj["verbose"] = True` (e.g., by adding `--verbose` to the test group or pre-populating `ctx.obj`) and asserts that the traceback appears in stderr output when an exception is raised. Alternatively, document explicitly that this path is exercised by an integration test.

---

#### EXERCISE: Unused `_invoke` helper ignores its own `cwd` parameter
- File: tests/unit/test_init_cmd.py:112
- Issue: `TestInitCmd._invoke` accepts a `cwd: Path` parameter but ignores it entirely — it creates a bare `CliRunner` and invokes without changing directory. The method is never called by any test in the class; all tests use `runner.invoke` directly. This is dead code with a misleading signature.
- Severity: LOW
- Action: Delete `_invoke`. It was never wired up and its `cwd` parameter implies a capability it does not provide. If a directory-setting helper is needed later, it should actually use `os.chdir` or `runner.isolated_filesystem`.

---

### None

No findings under: INTEGRITY, WEAKENING, SCOPE, ISOLATION.

- **Assertion honesty**: All asserted values (default field values, exit codes, string tokens) are traceable to the implementation source. No magic numbers or always-true assertions found.
- **Weakening**: No existing tests were modified. All test files are new for this milestone.
- **Scope alignment**: All imports (`sdi.config`, `sdi.cli`, `sdi.cli.init_cmd`) reference modules present in the implementation. `FeatureRecord` is correctly imported from `sdi.snapshot.model` per the M01 architecture decision documented in `CODER_SUMMARY.md`. No orphaned or stale imports detected.
- **Isolation**: All tests use `tmp_path` or `CliRunner.isolated_filesystem()` for fixture data. No test reads mutable pipeline artifacts (`CODER_SUMMARY.md`, `TESTER_REPORT.md`, build logs, etc.).
