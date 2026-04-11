## Test Audit Report

### Audit Summary
Tests audited: 1 file, 40 test functions (`tests/unit/test_assembly.py`)
Verdict: PASS

---

### Findings

#### COVERAGE: Round-trip verification omits new M07 fields
- File: `tests/unit/test_assembly.py:701` (`test_written_snapshot_is_readable`)
- Issue: The disk round-trip test reads a snapshot back and only asserts on
  `snapshot_version`, `timestamp`, and `file_count`. It does not verify that
  `graph_metrics`, `pattern_catalog`, or `partition_data` — the three fields
  added by M07 to `Snapshot` — survive `to_dict()`/`from_dict()` correctly.
  These fields are the primary M07 additions; their round-trip fidelity is the
  core correctness guarantee for `compute_delta()` to work on reloaded snapshots.
  A silent key truncation or serialization bug would go undetected.
- Severity: MEDIUM
- Action: Extend `test_written_snapshot_is_readable` to also assert
  `read_back.graph_metrics == result.graph_metrics`,
  `read_back.pattern_catalog == result.pattern_catalog`, and
  `read_back.partition_data == result.partition_data`. Or add a dedicated
  `test_new_m07_fields_survive_round_trip` test that assembles a snapshot with
  non-empty community and catalog data and verifies exact field equality after
  read-back.

#### SCOPE: Integration-style tests placed in unit test module
- File: `tests/unit/test_assembly.py:682` (`TestAssembleSnapshotRealDiskRoundTrip`)
- Issue: The four tests in this class perform real filesystem I/O with no
  mocking of the storage layer. They depend on `write_snapshot`, `read_snapshot`,
  `list_snapshots`, and `enforce_retention` all functioning correctly — a
  multi-module dependency chain. Per CLAUDE.md: "Unit tests (`tests/unit/`) mock
  external dependencies (filesystem, git, tree-sitter) where needed." Tests that
  rely on the storage layer behaving correctly are integration tests by the
  project's own definition.
- Severity: LOW
- Action: Move `TestAssembleSnapshotRealDiskRoundTrip` to
  `tests/integration/test_assembly_disk.py`, or fold into the existing
  `tests/integration/test_full_pipeline.py`. The unit test file should remain
  fully mocked at the storage boundary.

#### COVERAGE: Config hash exclusion not verified for all non-analysis sections
- File: `tests/unit/test_assembly.py:233` (`TestComputeConfigHash`)
- Issue: Tests verify that `output.*` and `snapshots.*` fields do not affect
  the config hash, but do not verify that `thresholds.*` and `change_coupling.*`
  are also excluded. Both sections are present in `SDIConfig` and are not
  included in `_compute_config_hash()`'s `analysis_cfg` dict (`assembly.py:43`).
  A future accidental addition of these sections to the hash would go undetected.
- Severity: LOW
- Action: Add `test_insensitive_to_thresholds_pattern_entropy_rate` and
  `test_insensitive_to_change_coupling_min_frequency` to `TestComputeConfigHash`.

#### NAMING: One test name does not encode the expected outcome
- File: `tests/unit/test_assembly.py:458` (`test_config_hash_is_set`)
- Issue: "Is set" is underspecified — it doesn't communicate what value is
  expected or what invariant is being asserted. The test actually verifies that
  the `config_hash` on the returned snapshot equals the value produced by calling
  `_compute_config_hash(cfg)` on the same config object. Compare to peer tests:
  `test_snapshot_version_is_current`, `test_commit_sha_preserved` — both encode
  the scenario and the expected invariant clearly.
- Severity: LOW
- Action: Rename to `test_config_hash_matches_computed_hash_of_input_config`.

---

### Rubric Notes (no findings)

**Assertion Honesty** — All assertions trace to real implementation logic.
Numeric literals (`16`, `4`, `7`, `2`) are derived from fixture inputs or
constants imported from the implementation (`SNAPSHOT_VERSION`). Config hash
sensitivity/insensitivity assertions match exactly what `_compute_config_hash()`
includes and excludes in `assembly.py:43–58`. No `assertTrue(True)` or
`assertEqual(x, x)` style vacuous assertions.

**Edge Case Coverage** — Adequate for the assembly scope. Covered: empty records,
`community=None`, `commit_sha=None`, first-snapshot null deltas (all four
dimensions), path traversal rejection with `SystemExit(2)`, retention enforcement
ordering (write-before-retain), and retention limit enforcement on real disk.
Delta correctness edge cases (identical snapshots → zeros, version mismatch →
warning+null deltas) are appropriately delegated to `test_delta.py`.

**Implementation Exercise** — Mocking is targeted. The storage layer
(`write_snapshot`, `read_snapshot`, `list_snapshots`, `enforce_retention`) is
mocked in all unit tests, keeping the assembly logic under test without coupling
to storage correctness. `TestAssembleSnapshotRealDiskRoundTrip` inverts this
by running with no mocks to verify the full chain. The real function
`_compute_config_hash` is called directly throughout `TestComputeConfigHash`
with no mocking at all.

**Test Weakening** — Not applicable. `test_assembly.py` is a new file (`??` in
git status). No prior version exists to weaken. TESTER_REPORT.md labels it
"Modified" but that is a documentation inaccuracy, not a test integrity issue.

**Test Naming** — 39 of 40 test names clearly encode both scenario and expected
outcome following the `test_<condition>_<expected_result>` pattern. One
exception noted under NAMING above.

**Scope Alignment** — All imports resolve to symbols present in the current
codebase. The `assemble_snapshot(records, graph_metrics, community, catalog,
config, commit_sha, timestamp, repo_root)` signature in tests matches the
implemented signature at `assembly.py:99`. The architecture change documented in
CODER_SUMMARY.md (removing `graph: igraph.Graph`, adding `repo_root: Path`) is
correctly reflected throughout the test file.

**Test Isolation** — All tests use `tmp_path` (pytest's ephemeral temp
directory) or purely in-memory objects. No test reads live project files,
pipeline logs, CI artifacts, or any mutable project state. Pass/fail outcome is
fully independent of prior pipeline runs or repo state.
