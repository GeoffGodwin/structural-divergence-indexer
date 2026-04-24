## Test Audit Report

### Audit Summary
Tests audited: 4 files, 52 test functions
Verdict: PASS

---

### Findings

#### NAMING: Misleading symlink label on a dotdot-only test
- File: tests/unit/test_helpers.py:74
- Issue: `test_traversal_via_symlink_component_raises_sysexit_2` uses `../../secrets/credentials` as input — a plain dotdot traversal with no actual symlink involved. The name implies a distinct symlink-resolution scenario that the test does not exercise; a reader searching for symlink coverage would falsely believe it exists.
- Severity: LOW
- Action: Rename to `test_deep_dotdot_traversal_raises_sysexit_2`. If symlink traversal genuinely needs coverage, add a separate test that creates a real symlink via `tmp_path` and verifies `resolve()` does not follow it out of `repo_root`.

#### INTEGRITY: Vacuous negation assertions shadow real check
- File: tests/unit/test_helpers.py:83
- Issue: `test_sysexit_code_is_2_not_1_or_3` asserts `exc_info.value.code == 2` (correct), then adds `assert exc_info.value.code != 1` and `assert exc_info.value.code != 3`. Both trailing assertions are logically impossible to fail once the equality passes — they add zero detection value and create an illusion of additional verification.
- Severity: LOW
- Action: Remove the two `!= ` assertions. The equality assertion alone is the correct and sufficient check.

#### COVERAGE: Retention assertion uses loose inequality (carried from M07 audit)
- File: tests/integration/test_full_pipeline.py:175
- Issue: `test_retention_enforced` asserts `assert len(snapshot_files) <= 2` with `retention = 2` and 4 snapshots written. The correct expectation is exactly 2. The `<=` form allows 0 or 1 remaining files to pass, masking an over-deletion regression.
- Severity: LOW
- Action: Change `assert len(snapshot_files) <= 2` to `assert len(snapshot_files) == 2`.

---

### Rubric Notes (no additional findings)

**Assertion Honesty** — All assertions derive from real implementation calls. Specific cross-checks:
- `resolve_snapshots_dir` returns `repo_root / config.snapshots.dir` when within bounds (`_helpers.py:38`); happy-path assertions are exact equality. ✓
- `run_checks` breach logic is `value is not None and value > threshold` (`check_cmd.py:116`); `test_value_equal_to_threshold_ok` correctly asserts equal does NOT exceed. ✓
- `_effective_threshold` uses `max(base, override_val)` (`check_cmd.py:74`); `test_override_does_not_lower_threshold` asserts a lower override does not tighten — consistent with `max`. ✓
- `_build_overrides` in `config.py:200–202` skips entries where `expires < today`; `test_expired_override_does_not_raise_threshold` calls the real function, asserts the expired key is absent, then invokes `run_checks` to confirm the base threshold applies. ✓
- `trend_cmd.py:103–112` passes `requested = list(dimensions)` to `compute_trend`; `test_trend_dimension_filter` asserts `set(data["dimensions"].keys()) == {"pattern_entropy"}` which would fail if filtering is absent. Verified against `compute_trend` implementation (`snapshot/trend.py:71–84`). ✓
- `diff_cmd.py:_load_pair` raises `SystemExit(1)` when `resolve_snapshot_ref` returns `None` (`diff_cmd.py:57–62`); `test_diff_invalid_ref_a_exits_1` and `test_diff_invalid_ref_b_exits_1` pass a non-matching string prefix ("no_such_prefix") for each slot and verify exit code 1. `resolve_snapshot_ref` exhausts numeric parse and prefix scan, then returns None — confirmed in `_helpers.py:119–124`. ✓

**Edge Case Coverage** — `test_helpers.py` covers four path-traversal shapes (two-level dotdot against `tmp_path`, one-level dotdot from a sub-directory root, absolute path outside root, deep dotdot path) plus three happy paths. `test_check_cmd.py` covers null deltas, zero threshold with null delta, below/equal/above threshold, negative delta (always ok), all four dimensions checked, active override, override not lowering threshold, highest of multiple overrides wins, dimension isolation, and expired override end-to-end. `test_cli_output.py` adds invalid ref_a and invalid ref_b exit-1 paths for diff. `test_full_pipeline.py` adds the trend dimension filter end-to-end path.

**Implementation Exercise** — No over-mocking. `test_helpers.py` calls `resolve_snapshots_dir` directly. `test_check_cmd.py` calls `run_checks`, `CheckResult.to_dict`, and `_build_overrides` directly. `test_cli_output.py` invokes real CLI commands via `CliRunner` with snapshots injected through `write_snapshot`. `test_full_pipeline.py` runs the complete 5-stage pipeline against controlled source files with no mocked dependencies.

**Test Weakening** — No existing assertions were removed or broadened in any audited file. The five new tests (`test_expired_override_does_not_raise_threshold`, `test_diff_invalid_ref_a_exits_1`, `test_diff_invalid_ref_b_exits_1`, `test_trend_dimension_filter`, and the nine `test_helpers.py` tests) are all additive.

**Test Naming** — 51 of 52 names clearly encode scenario and expected outcome. The one exception (symlink naming) is documented under NAMING above.

**Scope Alignment** — All imports resolve to symbols present in the current codebase. `CheckResult`, `run_checks` exist in `sdi.cli.check_cmd`. `_build_overrides` is private but imported for white-box verification of the expiry-filtering contract — intentional and appropriate for this unit test. No references to the deleted `.tekhton/test_dedup.fingerprint` appear in any audited test file.

**Test Isolation** — All four files use `tmp_path`-based fixtures or purely in-memory objects. No test reads live pipeline logs, CI artifacts, or mutable project-state files. Pass/fail outcome is fully independent of prior pipeline runs.
