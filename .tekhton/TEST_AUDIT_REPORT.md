## Test Audit Report

### Audit Summary
Tests audited: 5 files, 60 test functions
Verdict: PASS

Files audited:
- `tests/integration/test_completion_cmd.py` (15 tests)
- `tests/unit/test_init_cmd.py` (13 tests)
- `tests/conftest.py` (fixtures and helpers — no test functions)
- `tests/integration/test_full_pipeline.py` (15 tests across 4 classes)
- `tests/integration/test_multi_snapshot.py` (9 tests across 2 classes)

Implementation files cross-referenced:
- `src/sdi/cli/completion_cmd.py`
- `src/sdi/cli/init_cmd.py`
- `src/sdi/cli/_helpers.py`
- `src/sdi/cli/check_cmd.py`
- `src/sdi/cli/boundaries_cmd.py`
- `tests/fixtures/setup_fixture.py`

---

### Findings

#### INTEGRITY: Parametrized completion tests use implementation dict as oracle
- File: `tests/integration/test_completion_cmd.py:44-51` (`test_completion_eval_line_in_output`)
- File: `tests/integration/test_completion_cmd.py:74-82` (`test_completion_hint_prefixed_with_hash`)
- Issue: Both parametrized tests import `_INSTRUCTIONS` from `sdi.cli.completion_cmd`
  and assert that `_INSTRUCTIONS[shell][0]` (or `f"# {_INSTRUCTIONS[shell][1]}"`)
  appears in `result.output`. Since `completion_cmd` also reads from `_INSTRUCTIONS`
  to produce its output (`completion_cmd.py:42-44`), the assertion is tautological:
  it is guaranteed to pass as long as the command runs without crashing. A wrong eval
  line (e.g., incorrect env-var name for a shell) would still produce a passing test.
  Content validation is only provided by the exact-match tests at lines 54–66 and
  85–97, which hard-code expected strings independently of the implementation dict.
- Severity: MEDIUM
- Action: The parametrized tests are redundant given the exact-match tests and should
  be removed, OR rewritten to assert a structural property (e.g., output contains
  exactly one non-comment line per shell) without re-importing `_INSTRUCTIONS`. The
  exact-match tests already cover all three shells individually and are sufficient.

#### COVERAGE: stderr/stdout channel routing is not verified in completion tests
- File: `tests/integration/test_completion_cmd.py:17-20, 74-97, 105-114`
- Issue: The `runner` fixture creates `CliRunner()` without an explicit `mix_stderr`
  argument. Click 8.x defaults to `mix_stderr=True`, which folds stderr into
  `result.output`. The hint tests verify the hint appears somewhere in `result.output`
  but cannot distinguish whether it was emitted to stderr (correct per CLAUDE.md rule 11:
  `click.echo(f"# {hint}", err=True)`) versus stdout (wrong). The eval-line/hint
  ordering test (`test_completion_eval_line_before_hint:105-114`) similarly conflates
  stdout and stderr. If the implementation mistakenly swapped the `err=True` argument,
  all existing tests would still pass.
- Severity: MEDIUM
- Action: (1) Change `return CliRunner()` to `return CliRunner(mix_stderr=True)` to
  document the dependency explicitly. (2) Add a complementary test using
  `CliRunner(mix_stderr=False)`: assert the eval line IS in `result.output` (stdout)
  and the hint IS NOT in `result.output` (must be on stderr only).

#### COVERAGE: TTY + one explicit flag path is untested in init_cmd tests
- File: `tests/unit/test_init_cmd.py`
- Issue: The prompt condition in `_maybe_install_hooks` is
  `if not install_post_merge and not install_pre_push and sys.stdin.isatty()`.
  When one flag is True and the caller is on a TTY, all prompting is silently bypassed
  and the other hook is skipped. This is correct behavior but non-obvious and untested.
  `test_maybe_install_hooks_flag_bypasses_tty_check` covers non-TTY + one flag;
  the symmetric TTY + one flag case is absent.
- Severity: LOW
- Action: Add one test: `mock_stdin.isatty() = True`, `install_post_merge=True`,
  `install_pre_push=False` → `click.confirm` never called, post-merge hook installed,
  pre-push hook absent. This confirms any explicit flag suppresses all TTY prompting.

#### COVERAGE: `test_check_tight_thresholds_exits_10` relies on implicit fixture assumption
- File: `tests/integration/test_multi_snapshot.py:214-241`
- Issue: The test writes `pattern_entropy_rate = 0.001` and asserts exit code 10,
  which requires `pattern_entropy_delta > 0.001` after adding drift files. This is
  an implicit assumption: it depends on `_add_drift_files` producing at least one new
  structural hash not present in the evolving fixture baseline. If the evolving fixture
  is later extended with similar error-handling patterns, the drift files may stop
  producing a detectable delta and the test would silently return exit 0 instead of 10,
  reversing its behavioral guarantee without a clear failure message. The test passes
  currently (774/0 per tester report) but is brittle.
- Severity: LOW
- Action: Add an intermediate assertion: after the second snapshot, read it directly
  via `_latest_by_mtime` and assert `snap2.divergence.pattern_entropy_delta > 0.001`
  before running `sdi check`. This provides a clear failure mode ("delta too small")
  separate from "check returned wrong exit code".

---

### Rubric Notes (no findings — informational)

**1. Assertion Honesty — PASS (with MEDIUM caveat above)**
All assertions beyond the flagged parametrized tests derive from real implementation
logic or hard-coded behavioral contracts. Representative examples:
- `test_infer_boundaries_from_snapshot_yaml_contains_cluster_names` asserts
  `"cluster_0"` and `"cluster_1"` — correct: `_partition_to_proposed_yaml`
  (`boundaries_cmd.py:68`) generates names via `f"cluster_{cid}"` from partition
  `[0, 0, 1]`, producing clusters 0 and 1.
- `test_infer_boundaries_from_snapshot_yaml_contains_file_paths` checks for
  `"src/a.py"` or `"src/b.py"` or `"src/c.py"` — correct: `_partition_to_proposed_yaml`
  emits each path from `partition_data["vertex_names"]` (`boundaries_cmd.py:70-72`).
- `assert len(data["checks"]) == 4` (`test_check_json_output_structure:256`) — correct:
  `run_checks` in `check_cmd.py:93-118` produces exactly 4 `CheckResult` entries,
  one per SDI dimension.
- `assert "→" in result.output` — the diff command text formatter produces this arrow.
- `assert "No boundary spec found" in result.output` — matches `_do_show` literal at
  `boundaries_cmd.py:88`.

**2. Edge Case Coverage — PASS**
`test_init_cmd.py`: TTY yes/yes, yes/no, no/no, prompt call count, non-TTY no flags,
flag bypasses TTY, missing hooks dir. `_infer_boundaries_from_snapshot`: missing
snapshots dir, empty snapshots dir, snapshot with empty `partition_data`, snapshot
missing `vertex_names`, and full success path. `test_completion_cmd.py`: all three
valid shells, invalid shell (`powershell`), content presence, output ordering.
`test_full_pipeline.py`: retention enforcement (write 4, keep ≤ 2), idempotent init,
first-snapshot null deltas, two-snapshot diff, trend dimension filter.

**3. Implementation Exercise — PASS**
`_maybe_install_hooks` tests call through to the real `install_post_merge_hook` /
`install_pre_push_hook` functions (`_hooks.py`), which write actual files into a temp
`.git/hooks/` directory; only `sys.stdin.isatty` and `click.confirm` are mocked —
correctly scoped. `_infer_boundaries_from_snapshot` happy-path tests call the real
function which imports and calls `_partition_to_proposed_yaml` (`boundaries_cmd.py:57`,
verified present). Integration tests in `test_full_pipeline.py` and
`test_multi_snapshot.py` invoke real tree-sitter parsing, igraph operations, and
filesystem writes with no mocking.

**4. Test Weakening — PASS**
All five audited files contain exclusively new tests or additions to new files.
No pre-existing test assertion was loosened, removed, or replaced with a broader check.

**5. Test Naming — PASS**
All test function names encode both the scenario and the expected outcome.
Representative: `test_maybe_install_hooks_tty_yes_yes_installs_both`,
`test_maybe_install_hooks_missing_hooks_dir_is_noop`,
`test_infer_boundaries_snapshot_no_vertex_names_returns_none`,
`test_completion_invalid_shell_exits_nonzero`,
`test_check_tight_thresholds_exits_10`,
`test_boundaries_propose_exits_1_without_snapshot`.

**6. Scope Alignment — PASS**
All imports verified against current implementation:
- `POST_MERGE_MARKER`, `PRE_PUSH_MARKER` — `src/sdi/cli/_hooks.py` ✓
- `_infer_boundaries_from_snapshot`, `_maybe_install_hooks` — `src/sdi/cli/init_cmd.py:179, 223` ✓
- `SNAPSHOT_VERSION`, `DivergenceSummary`, `Snapshot` — `src/sdi/snapshot/model.py` ✓
- `write_snapshot` — `src/sdi/snapshot/storage.py` ✓
- `_INSTRUCTIONS` — `src/sdi/cli/completion_cmd.py:7` ✓
- `cli` root group, `completion_cmd` registered — `src/sdi/cli/__init__.py` ✓
- `list_snapshots`, `read_snapshot` — `src/sdi/snapshot/storage.py` ✓
- `create_evolving_fixture` — `tests/fixtures/setup_fixture.py:130` ✓
No references to deleted files (`.tekhton/test_dedup.fingerprint`). The pre-verified
STALE-SYM entries (21 items across `conftest.py` and `test_full_pipeline.py`) are
**all false positives** from a scanner that cannot parse Python import syntax:
every flagged symbol (`Any`, `CliRunner`, `Path`, `SNAPSHOT_VERSION`, `catalog`,
`fingerprint`, `leiden`, `model`, `os`, `parsing`, `pathlib`, `pytest`, `storage`,
`testing`, `typing`) is properly resolved via explicit `import` or `from … import`
statements visible in the respective files.

**7. Test Isolation — PASS**
All tests use `tmp_path`-rooted fixtures or `CliRunner` (in-process, no filesystem side
effects). `multilang_project` and `high_entropy_project` fixtures use `shutil.copy` into
`tmp_path` — they do not mutate the source fixture directories. No test reads
`.tekhton/`, `.claude/logs/`, or any other mutable project-state file.
Pass/fail is fully independent of prior pipeline runs or repository state.

**Note on `_latest_by_mtime` helper correctness:**
The workaround for `list_snapshots` alphabetical-sort ambiguity
(`test_multi_snapshot.py:20-40`) is sound: `max(paths, key=lambda p: p.stat().st_mtime_ns)`
uses nanosecond resolution and is always correctly ordered. The empty-list guard
(`raise FileNotFoundError`) prevents silent failures. The TODO comment correctly
identifies this as a temporary workaround pending a native fix in `storage.py`.
