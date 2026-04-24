## Test Audit Report

### Audit Summary
Tests audited: 4 files, 44 test functions
Verdict: PASS

---

### Findings

#### NAMING: Misleading symlink label on a dotdot-only test
- File: tests/unit/test_helpers.py:74
- Issue: `test_traversal_via_symlink_component_raises_sysexit_2` uses `../../secrets/credentials` as input, which is a plain dotdot traversal with no actual symlink involved. The name implies a distinct symlink-resolution scenario that the test does not exercise; a reader searching for symlink coverage would falsely believe it exists.
- Severity: LOW
- Action: Rename to `test_two_level_dotdot_deep_path_raises_sysexit_2` (or similar) to describe what the test actually does. If symlink traversal needs coverage, add a separate test that creates a real symlink via `tmp_path` and verifies `resolve()` does not follow it out of `repo_root`.

#### INTEGRITY: Vacuous assertions shadow real check
- File: tests/unit/test_helpers.py:83–90
- Issue: `test_sysexit_code_is_2_not_1_or_3` asserts `exc_info.value.code == 2` (correct), then adds `assert exc_info.value.code != 1` and `assert exc_info.value.code != 3`. Both trailing assertions are logically impossible to fail once the equality check passes; they add zero detection value and create the illusion of additional verification.
- Severity: LOW
- Action: Remove the two `!= ` assertions. The equality assertion alone is the correct and sufficient check.

#### COVERAGE: Retention assertion uses loose inequality (carryover from prior audit)
- File: tests/integration/test_full_pipeline.py:175
- Issue: `test_retention_enforced` asserts `assert len(snapshot_files) <= 2` with `retention = 2` and 4 snapshots written. The correct expectation is exactly 2. The `<=` form allows 0 or 1 remaining files to pass, masking an over-deletion regression. This finding was raised in the M07 audit and has not been addressed.
- Severity: LOW
- Action: Change `assert len(snapshot_files) <= 2` to `assert len(snapshot_files) == 2`.

---

### Rubric Notes (no findings)

**Assertion Honesty** — All assertions derive from real implementation calls with meaningful inputs. Specific cross-checks against implementation:
- `resolve_snapshots_dir` returns `repo_root / config.snapshots.dir` unmodified when within bounds (`_helpers.py:38`); happy-path assertions (`result == tmp_path / ".sdi" / "snapshots"`) are exact. ✓
- `isinstance(data, dict)` guard in `_partition_cache.py:45` is tested indirectly through the full-pipeline tests (partition cache is read on warm start). ✓
- `run_checks` breach logic is `value is not None and value > threshold` (`check_cmd.py:116`); `test_value_equal_to_threshold_ok` correctly asserts equal does NOT exceed. ✓
- `_effective_threshold` uses `max(base, override_val)` (`check_cmd.py:74`); `test_override_does_not_lower_threshold` asserts a lower override does not tighten — consistent with `max`. ✓
- `_build_overrides` in `config.py:200–202` skips entries where `expires < today`; `test_expired_override_does_not_raise_threshold` calls the real function and asserts the key is absent before invoking `run_checks`. ✓
- `trend_cmd.py:103–112` passes `requested = list(dimensions)` to `compute_trend`; `test_trend_dimension_filter` asserts `set(data["dimensions"].keys()) == {"pattern_entropy"}` which fails if filtering is absent. ✓
- `diff_cmd.py:_load_pair` raises `SystemExit(1)` when `resolve_snapshot_ref` returns `None` (`diff_cmd.py:57–62`); `test_diff_invalid_ref_a_exits_1` and `test_diff_invalid_ref_b_exits_1` pass a non-matching prefix and verify exit 1. ✓

**Edge Case Coverage** — `test_helpers.py` covers four path-traversal shapes (two-level dotdot, one-level dotdot from subdirectory, absolute path outside root, and deep dotdot path) plus three happy paths. `test_check_cmd.py` covers null deltas, zero threshold with null, below/equal/above, negative delta (always OK), all four dimensions, active override, override does not lower, highest of multiple overrides wins, dimension isolation, and expired-override end-to-end. `test_cli_output.py` adds invalid ref_a and ref_b exit-1 paths for diff. `test_full_pipeline.py` adds the trend dimension filter end-to-end path.

**Implementation Exercise** — No over-mocking in any file. `test_helpers.py` calls `resolve_snapshots_dir` directly. `test_check_cmd.py` calls `run_checks`, `CheckResult.to_dict`, and `_build_overrides` directly. `test_cli_output.py` invokes real CLI commands via `CliRunner` with snapshots injected through `write_snapshot`. `test_full_pipeline.py` runs the complete 5-stage pipeline against controlled source files with no mocked dependencies.

**Test Weakening** — `test_full_pipeline.py` has AM status (staged additions + unstaged modifications); the new test `test_trend_dimension_filter` was added cleanly. No existing assertions were removed or broadened in any audited file.

**Test Naming** — 43 of 44 names clearly encode scenario and expected outcome. The one exception is documented under NAMING above.

**Scope Alignment** — All imports resolve to symbols present in the current codebase. `CheckResult`, `run_checks` exist in `sdi.cli.check_cmd`. `_build_overrides` is a private function imported for white-box verification of the expiry-filtering contract — intentional and appropriate. No references to deleted files (`CODER_SUMMARY.md`, `REVIEWER_REPORT.md`, `SECURITY_REPORT.md`) appear in any audited test file.

**Test Isolation** — All four files use `tmp_path`-based fixtures (`git_repo_dir`, `sdi_project_dir`, `sdi_project_with_snapshot`, `initialized_project`) or purely in-memory objects. No test reads live pipeline logs, CI artifacts, or mutable project-state files. Pass/fail outcome is fully independent of prior pipeline runs.
