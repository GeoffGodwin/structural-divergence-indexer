## Test Audit Report

### Audit Summary
Tests audited: 7 files, ~179 test functions
Verdict: PASS

---

### Findings

#### NAMING: Misleading test name implies symlink testing
- File: `tests/unit/test_helpers.py:74`
- Issue: `test_traversal_via_symlink_component_raises_sysexit_2` references "symlink" in both name and comment but the test creates no symlink — it only tests a `..`-based traversal path (`../../secrets/credentials`). The implementation (`Path.resolve().is_relative_to()`) handles both `..` segments and symlinks, so the behavior under test is correct, but a reader will expect a symlink fixture that does not exist.
- Severity: LOW
- Action: Rename to `test_dotdot_traversal_raises_sysexit_2` and remove the misleading comment.

---

#### EXERCISE: Test couples to private function `_build_overrides` from `sdi.config`
- File: `tests/unit/test_check_cmd.py:171`
- Issue: `test_expired_override_does_not_raise_threshold` imports `_build_overrides` (an underscore-prefixed, private function) from `sdi.config` and calls it directly to construct test state. The test correctly verifies the end-to-end expired-override contract, but coupling to a private function means any rename or internal restructuring of `_build_overrides` breaks the test's setup code, potentially surfacing as a false failure during legitimate refactors. The first assertion (`assert "old_migration" not in overrides`) is also testing an internal intermediate state rather than the public contract.
- Severity: LOW
- Action: Express the expired-override contract through the public config loading surface: write a `.sdi/config.toml` with the expired override into a `tmp_path` directory, call `load_config(project_dir)`, then verify `run_checks` raises a breach. This removes the private-function coupling and tests the full five-level config precedence chain.

---

### None (all remaining rubric items)

No INTEGRITY, SCOPE, WEAKENING, COVERAGE, or ISOLATION violations were found beyond the two LOW items above.

---

### Rubric Notes

**1. Assertion Honesty — PASS**
All assertions derive from real implementation logic. Selected cross-checks:

- `test_intent_divergence_total_violations_added_to_partition_count` (`test_delta.py:254`) asserts `== 7` for inter-cluster count 3 + `intent_divergence.total_violations` 4. Traced to `_count_boundary_violations()` in `delta.py:105–110`: `partition_count + intent_count`. ✓
- `test_get_file_fingerprints_cache_hit_returns_cached_data` (`test_fingerprint_cache.py:289`) distinguishes cache-hit from cache-miss by pre-writing a sentinel value `"cached_sentinel_1122"` that differs from what fresh computation would produce (`"computed_different_99"`). A cache-miss regression would flip the assertion. ✓
- `test_active_hashes_derived_from_record_content_hashes` (`test_assembly.py:979`) accesses `mock_parse_cleanup.call_args[0][1]` and asserts `== {hash_a, hash_b}`. Traced to `assembly.py:159`: `active_hashes = {r.content_hash for r in records if r.content_hash}`. ✓
- `test_expired_override_does_not_raise_threshold` (`test_check_cmd.py:164`) passes `expires="2020-01-01"` to `_build_overrides`. `config.py:200–202` skips entries where `expires < today`. Test verifies key absence then exercises `run_checks` end-to-end. ✓
- `test_trend_dimension_filter` (`test_full_pipeline.py:148`) asserts `set(data["dimensions"].keys()) == {"pattern_entropy"}`. Would fail if `trend_cmd.py` filtering is absent or over-inclusive. ✓
- `test_diff_invalid_ref_a_exits_1` (`test_cli_output.py:137`) passes `"no_such_prefix"` as ref_a. `resolve_snapshot_ref` in `_helpers.py:119–124` exhausts integer parse then prefix scan, returns None; `load_snapshot_by_ref` raises `SystemExit(1)`. ✓

**2. Edge Case Coverage — PASS**
`test_fingerprint_cache.py` covers: missing dir (cache miss), hash not found (cache miss), corrupt JSON (None returned), non-list JSON (None returned), empty fingerprint list, deeply nested cache dir, cache-hit vs cache-miss distinction, `min_nodes` filtering, empty `content_hash` fallthrough (no cache lookup, no write). `test_delta.py` covers: empty partition dict (zero), zero intent violations, missing `intent_divergence` key, additive semantics (not deduplicated), first-snapshot null deltas, incompatible version. `test_assembly.py` covers: empty records (file_count=0, empty breakdown), community=None (empty partition_data), path traversal rejection (SystemExit 2), empty `content_hash` excluded from active_hashes, all-empty hashes giving empty active set, call ordering (write < retain < cleanup). `test_check_cmd.py` covers: null delta at threshold=0 (no breach), negative delta, all four dimensions checked, active/expired/multiple/dimension-isolated overrides.

**3. Implementation Exercise — PASS**
`TestAttachIntentDivergence` writes a real YAML file and calls `_attach_intent_divergence()` against the live `load_boundary_spec` + `compute_intent_divergence` pipeline — no mocking of the computation chain. `TestAssembleSnapshotRealDiskRoundTrip` writes actual snapshot files to a temp directory and reads them back using the real storage layer (no mocking). `test_fingerprint_cache.py` calls all four public cache functions against real temp-directory I/O. `TestCountBoundaryViolationsIntentDivergence` calls `_count_boundary_violations()` and `compute_delta()` directly with constructed inputs.

**4. Test Weakening — PASS**
All modified test files were examined for removed or broadened assertions. Existing `test_delta.py` test classes use the `_partition()` helper which omits `intent_divergence`; their assertions remain correct because `_count_boundary_violations` returns 0 for that key when absent. No assertions were removed or widened in any audited file. `test_assembly.py` additions are purely additive (new test classes at end of file).

**5. Test Naming — PASS**
Except for the one LOW item above, all test names encode both the scenario and the expected outcome. Representative examples: `test_get_file_fingerprints_cache_hit_returns_cached_data`, `test_empty_content_hash_excluded_from_active_hashes`, `test_cleanup_called_after_write_and_retention`, `test_misplaced_file_detected_via_assembly`, `test_no_violations_when_partition_matches_spec`, `test_diff_invalid_ref_b_exits_1`.

**6. Scope Alignment — PASS**
All imports verified against current implementation:
- `read_fingerprint_cache`, `write_fingerprint_cache`, `cleanup_orphan_fingerprint_cache`, `get_file_fingerprints` — `src/sdi/patterns/_fingerprint_cache.py` (NEW, line 28+) ✓
- `_attach_intent_divergence`, `_compute_config_hash`, `assemble_snapshot` — `src/sdi/snapshot/assembly.py` (line 33, 101, 165) ✓
- `_count_boundary_violations`, `compute_delta` — `src/sdi/snapshot/delta.py` (line 91, 152) ✓
- `resolve_snapshots_dir` — `src/sdi/cli/_helpers.py` (line 25) ✓
- `_build_overrides` — `src/sdi/config.py` (line 195) ✓
- `_do_export`, `_do_show`, `_partition_to_proposed_yaml`, `_spec_as_text` — `boundaries_cmd.py` ✓
- `BoundarySpec`, `AllowedCrossDomain`, `AspirationalSplit`, `LayersSpec`, `ModuleSpec` — `detection/boundaries.py` ✓

No references to deleted files (`.tekhton/ARCHITECT_PLAN.md`, `.tekhton/test_dedup.fingerprint`) appear in any audited test file.

**7. Test Isolation — PASS**
All tests use `tmp_path`-rooted fixtures or in-memory objects exclusively. `sdi_project_dir` and `sdi_project_with_snapshot` are both rooted in `tmp_path` (conftest.py:82–94, 177–186). `test_full_pipeline.py` defines its own `initialized_project` fixture from `tmp_path` (line 47–65). No test reads `.tekhton/`, `.claude/logs/`, CI artifacts, live build reports, or any other mutable project-state file. Pass/fail outcome is fully independent of prior pipeline runs or repository state.
