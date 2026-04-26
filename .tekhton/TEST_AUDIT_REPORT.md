## Test Audit Report

### Audit Summary
Tests audited: 2 files, 37 test functions (23 unit + 14 integration)
Verdict: PASS

---

### Findings

#### COVERAGE: Tester report does not distinguish skipped vs. passed for adapter-gated tests
- File: tests/integration/test_shell_pipeline.py (all 4 test classes)
- Issue: All new integration test classes (`TestShellPipeline.test_edge_count_at_least_one`,
  `TestShellHeavyGraph`, `TestShellGraphFixture`, `TestShellNoEdges`) are decorated with
  `@requires_shell_adapter`. The TESTER_REPORT claims "Passed: 48 Failed: 0" without
  stating whether tree-sitter-bash was installed or whether these tests executed vs. were
  skipped. The count of 48 is consistent with the 23 new unit tests (no grammar needed)
  plus pre-existing tests — meaning all 14 new integration tests may have been *skipped*,
  not passed. M15 acceptance criteria (`edge_count >= 12`, `component_count <= 4`) would
  therefore be unverified at the integration level.
- Severity: MEDIUM
- Action: Re-run the test suite with tree-sitter-bash installed and confirm the four new
  integration classes execute and pass (not just skip). Update TESTER_REPORT with
  explicit skipped/passed/failed counts. No test code changes required.

#### COVERAGE: `TestShellHeavyGraph` uses a weak lower-bound assertion for connectivity
- File: tests/integration/test_shell_pipeline.py:117
- Issue: `assert data["graph_metrics"]["component_count"] <= data["file_count"] - 1`
  is mathematically equivalent to `component_count < file_count`, meaning it passes
  whenever a single edge exists in any 10-node graph. For a fixture named "shell-heavy"
  (10 files with multiple source edges), this bound does not adequately verify the
  degree of connectivity the fixture is designed to demonstrate.
- Severity: LOW
- Action: Tighten to a fixture-specific bound, e.g. `<= 5` (half the file count). No
  implementation change required.

#### EXERCISE: `TestResolveShellImportDynamic` tests a code path the pipeline is designed to prevent
- File: tests/unit/test_graph_builder_shell.py:312–355
- Issue: The class docstring acknowledges that "these strings should never reach the
  resolver in normal operation" because the shell adapter's static-literal filter removes
  `$VAR`, `$(...)`, and backtick forms before building FeatureRecords. The seven tests
  verify defensive behavior for inputs that cannot arrive through the real pipeline.
  They provide no confidence in M15 behavior and test an unreachable branch of the
  resolver under normal operation.
- Severity: LOW
- Action: Tests are not incorrect and protect against future regressions if the
  shell adapter filter is weakened. Acceptable as-is; no removal required.

#### SCOPE: Pre-verified stale-symbol report is entirely false positives
- File: tests/integration/test_shell_pipeline.py
- Issue: The pre-audit orphan checker flagged `Path`, `conftest`, `json`, `pathlib`,
  `pytest`, `requires_shell_adapter`, `shutil`, and `stat` as unresolved symbols. All
  eight are present and correctly imported: `json`, `shutil`, `stat`, `pathlib` are
  Python stdlib (lines 9–12); `pytest` is the test framework (line 14); `Path` is
  from `pathlib` (line 10); `requires_shell_adapter` and `run_sdi` are defined at
  `tests/conftest.py:67` and `tests/conftest.py:199` respectively. The checker compares
  only against implementation source files and is not Python-import-aware.
- Severity: LOW
- Action: No test changes needed. The orphan checker's false-positive rate for stdlib
  and conftest symbols should disqualify it as a gate in future audits without a
  Python-aware import resolver.

---

### Verified Clean (no findings)

**1. Assertion Honesty — PASS**
Every numeric assertion traces to implementation logic. `result == "common.sh"` over
`"common.bash"` directly reflects `_SHELL_EXTENSIONS_FOR_FALLBACK = (".sh", ".bash")`
(builder.py:56) — an ordered tuple checked left-to-right. `g.es[0]["weight"] == 2`
follows from the `edge_weight_map` accumulation at builder.py:284–286. `result is None`
for `"common.zsh"` follows from `_KNOWN_SHELL_EXTS` containing `.zsh` (builder.py:60)
which causes extension fallback to be skipped. No assertion hard-codes a value that
cannot be traced to the implementation.

**2. Edge Case Coverage — PASS**
Unit suite covers: exact match, missing import, extensionless `.sh` fallback,
`.sh`-over-`.bash` preference, known-extension skip, `.bash`-only fallback, self-import
(counted but not an edge), empty imports, empty path set, cross-language sourcing, mixed
3-language dispatch, weighted duplicate edges, and determinism under reversed input
order. Integration suite covers: zero-source-edge shell repo (no crash), edge count
floor, connectivity lower bound, and the full shell-graph fixture at acceptance
thresholds.

**3. Implementation Exercise — PASS**
Unit tests call `_resolve_shell_import` and `build_dependency_graph` directly with
minimal `FeatureRecord` inputs — no mocking of any dependency. Integration tests run
the full SDI CLI pipeline (`run_sdi`) against real fixture files copied into `tmp_path`.
The shell dispatch arm in `build_dependency_graph` (builder.py:260–262), the extension
fallback loop (builder.py:187–191), and the weighted/unweighted edge accumulation paths
(builder.py:283–293) are all exercised by the unit suite.

**4. Test Weakening — PASS**
The integration file was modified by adding three new test classes and one test method
to an existing class. All pre-existing tests (`test_snapshot_detects_three_shell_files`,
`test_catalog_contains_error_handling_and_logging`) are unchanged. No assertion was
removed or broadened.

**5. Test Naming — PASS**
Names are descriptive and encode both scenario and expected outcome:
`test_extensionless_prefers_sh_over_bash`, `test_known_extension_skips_fallback`,
`test_self_import_not_counted_as_unresolved`, `test_mixed_language_three_edges`.
Integration test names map to acceptance criteria: `test_edge_count_at_least_12`,
`test_component_count_at_most_4`.

**6. Scope Alignment — PASS**
All imports are live: `_resolve_shell_import` and `build_dependency_graph` exist in
`src/sdi/graph/builder.py`; `FeatureRecord` exists in `src/sdi/parsing/__init__.py`;
`SDIConfig` exists in `src/sdi/config.py`. The deleted file
`.tekhton/test_dedup.fingerprint` is not referenced by either test file. No orphaned
or stale references.

**7. Test Isolation — PASS**
All integration tests copy fixture directories into `tmp_path` before use
(`_make_shell_project`, `shell_project` fixture, `no_source_project` fixture). No test
reads `.tekhton/`, `.claude/logs/`, live pipeline artifacts, or any mutable project
state. Pass/fail outcomes are fully independent of prior pipeline runs and repository
state.

**Edge count arithmetic for shell-graph fixture — independently verified**
Manual trace of `tests/fixtures/shell-graph/` sources yields 13 unique directed edges:
`entrypoint.sh` contributes 4 (→ common, deploy, rollback, status); `lib/common.sh`
contributes 2 (→ log.sh, util.sh via extensionless fallback); `cmd/deploy.sh`,
`cmd/rollback.sh` each contribute 3 (→ common, log, db); `cmd/status.sh` contributes 1
(→ common). All 8 nodes form one weakly-connected component. The `>= 12` edge threshold
and `<= 4` component bound in `TestShellGraphFixture` are both sound.
