### Milestone 18: Cross-Repo Validation Harness for Shell and TS
<!-- milestone-meta
id: "18"
status: "done"
-->


**Scope:** Add a validation suite that runs `sdi snapshot` against representative shell-heavy and TypeScript-heavy fixtures and asserts sanity invariants on edge counts, language-applicable categories, cluster topology, and pattern signal. The suite has two layers: (1) bundled fixtures that always run in CI to catch regressions of the M15/M16/M17 work, and (2) an optional opt-in harness that runs against the developer's local Tekhton and bifl-tracker checkouts when explicitly enabled, providing real-world calibration without making CI depend on external repos. The bundled fixtures encode the same structural shapes the user observed in production: a shell-heavy repo with cross-file `source` topology and a TS app with realistic import structure.

**Philosophy reminder (read first):** Per CLAUDE.md "Measurement over opinion," every assertion in this harness is a numeric invariant against snapshot output, not a judgment about code quality. Phrases like "sane," "healthy," "expected," or "reasonable" do not appear in test names or assertion messages — use "≥ N" / "= N" / "language X has non-zero per-language entropy." Per "Composable Unix tooling," the harness invokes `sdi snapshot` as a subprocess and inspects the JSON it writes, never imports SDI internals to compute expected values; this matches the integration tests in M14 (`tests/integration/test_shell_evolving.py`).

**Deliverables:**
- New bundled fixtures under `tests/fixtures/`:
  - `tests/fixtures/shell-heavy-realistic/` — **30 to 40 shell scripts** in three top-level directories (`bin/`, `lib/`, `cmd/`) plus a small `tests/` subdirectory for exercising M17:
    - Topology: each `bin/*.sh` sources 2–4 `lib/*.sh` files; `cmd/*.sh` sources `lib/common.sh` and one or two specialized libs; `lib/*.sh` files form a small DAG with at most 3 cross-`lib` edges.
    - Total `source` edges in the fixture: **between 45 and 60**, counted manually in a fixture README and asserted at test time.
    - Pattern instance distribution: at least 6 distinct `error_handling` shapes, 3 distinct `data_access` shapes, 4 distinct `logging` shapes, 2 distinct `async_patterns` shapes — chosen to exercise the full M14 detection set.
    - `tests/scenario_*.sh` (5 scripts) each containing a deliberately distinct `error_handling` shape so that excluding `tests/**` via M17 changes `pattern_entropy_by_language["shell"]` measurably.
  - `tests/fixtures/typescript-realistic/` — **15 to 25 TypeScript files** simulating a small backend service (the bifl-tracker shape):
    - One `src/index.ts` entrypoint, an `src/api/` directory with route handlers, an `src/db/` directory with model files, an `src/lib/` directory with utilities.
    - At least one `tsconfig.json` with `compilerOptions.paths` containing `@/*` aliases targeting `src/*` to exercise the alias resolver.
    - Each route handler imports from `@/db` and `@/lib`; models import from `@/lib`; utilities are leaves.
    - Total imports producing edges: **between 20 and 40**.
    - Pattern instance distribution: at least 3 distinct `error_handling` shapes (try/catch variations), 2 distinct `async_patterns` shapes (async functions, await), 2 distinct `logging` shapes (console.* calls).
- New integration test file `tests/integration/test_validation_shell_realistic.py` (gated by `requires_shell_adapter`):
  - Run `sdi init` then `sdi snapshot` against `shell-heavy-realistic/`. Assert:
    - `language_breakdown["shell"]` between 30 and 40 (the actual count from the fixture).
    - `graph_metrics.edge_count >= 45` (lower bound from fixture README).
    - `graph_metrics.component_count <= file_count // 5` (the fixture is intentionally well-connected; expect at most 1 component per 5 files).
    - `partition_data.cluster_count` between `2` and `file_count // 3` (Leiden produces non-trivial clusters; not 1, not file_count).
    - `pattern_entropy_by_language["shell"] >= 15` (sum of shell-applicable categories' distinct shapes).
    - `pattern_entropy_by_language` does **not** contain a key for any language with zero files in the fixture (e.g., no `"python"` key on a pure-shell fixture).
    - The `pattern_catalog.categories` has zero shapes under `class_hierarchy`, `context_managers`, and `comprehensions` (Python-only categories should never light up on a pure-shell repo even with any future adapter changes).
  - A second test in the same file runs the same fixture with `scope_exclude = ["tests/**"]` configured. Assert:
    - `pattern_entropy_by_language["shell"]` strictly less than the baseline run.
    - `graph_metrics.edge_count` and `graph_metrics.node_count` are **identical** to the baseline run (M17 leaves the graph alone).
    - `pattern_catalog.meta.scope_excluded_file_count == 5` (the five `tests/scenario_*.sh` files).
- New integration test file `tests/integration/test_validation_typescript_realistic.py`:
  - Run `sdi init` then `sdi snapshot` against `typescript-realistic/`. Assert:
    - `language_breakdown["typescript"]` between 15 and 25.
    - `graph_metrics.edge_count >= 20` (lower bound from fixture README).
    - `graph_metrics.component_count == 1` (the fixture is fully connected through `src/index.ts`).
    - `partition_data.cluster_count >= 2` (route + db + lib should form distinguishable clusters).
    - `pattern_entropy_by_language["typescript"] >= 5`.
    - `pattern_entropy_by_language` does not contain a `"shell"` key.
- Optional opt-in real-repo harness — new file `tests/integration/test_validation_real_repos.py`:
  - Skip the entire module unless `SDI_VALIDATION_TEKHTON` or `SDI_VALIDATION_BIFL` environment variables are set to absolute paths.
  - When `SDI_VALIDATION_TEKHTON` is set:
    - Verify the path is a directory and is a git repo (presence of `.git`). Skip with a clear message if not.
    - Run `sdi init` (idempotent — does not overwrite existing config) and `sdi snapshot` against the directory.
    - Assert `graph_metrics.edge_count >= 100` (Tekhton has dozens of `lib/*.sh` files sourcing each other; the floor is conservative).
    - Assert `pattern_entropy_by_language["shell"] >= 50`.
    - Assert `pattern_entropy_by_language` does not include any language with zero files.
  - When `SDI_VALIDATION_BIFL` is set:
    - Same path validation.
    - Assert `graph_metrics.edge_count >= 30`.
    - Assert `pattern_entropy_by_language["typescript"] >= 10`.
    - Assert post-M16 `pattern_entropy_by_language["typescript"]` is within 10% of a captured pre-M16 baseline (the no-regression invariant on the TS-heavy case). The baseline is captured during M16 implementation and stored as a JSON file in `tests/integration/fixtures/_baselines/bifl_tracker_pre_m16.json`. If the baseline file is absent, the test logs a warning and skips the regression assertion (this allows fresh checkouts to skip rather than fail).
  - The harness writes its outputs into `<repo>/.sdi/snapshots/` like a normal `sdi snapshot` run. Document this clearly in the module docstring; users opting in must be aware their repo will gain a `.sdi/` directory.
- Top-level documentation:
  - Add `docs/validation.md` (new file) describing the harness, the bundled fixtures' invariants, and the env-var protocol for the real-repo opt-in. Include a one-paragraph rationale: this work was added to close the gap exposed by dogfooding SDI on Tekhton in 2026-04, where shell-heavy repos produced degenerate graph and category signal.
  - Add a `CHANGELOG.md` entry: `Added: cross-repo validation harness with bundled shell-heavy and TypeScript-realistic fixtures; optional real-repo opt-in via SDI_VALIDATION_TEKHTON / SDI_VALIDATION_BIFL.`

**Acceptance criteria:**
- Both bundled-fixture test files pass when run with M15, M16, and M17 implemented. They fail with clear assertion messages when any of M15/M16/M17 is reverted (this is the reason the harness exists).
- Running with `M15 reverted`: `test_validation_shell_realistic.py` fails on the `edge_count >= 45` assertion (shell sources do not resolve, edge count drops to ~0).
- Running with `M16 reverted`: `test_validation_shell_realistic.py` fails on the `pattern_entropy_by_language["shell"]` assertion (the field does not exist on the snapshot).
- Running with `M17 reverted`: the second test in `test_validation_shell_realistic.py` fails on the `scope_excluded_file_count` assertion (the field does not exist).
- The opt-in real-repo harness is gated by env vars and produces no output (skips silently) in default CI runs.
- Real-repo harness against `SDI_VALIDATION_TEKHTON=/path/to/tekhton` (the user's actual repo at the time of writing) reports `edge_count` in the hundreds and `pattern_entropy_by_language["shell"]` in the dozens. The exact numbers are not in the assertion (they evolve with the user's repo); only the floors are.
- Real-repo harness against `SDI_VALIDATION_BIFL=/path/to/bifl-tracker` produces a snapshot whose `pattern_entropy_by_language["typescript"]` is within 10% of the captured pre-M16 baseline. The TS-side regression invariant is the most important assertion in this milestone.
- All numeric floors in the harness are documented with a comment explaining where the number comes from (fixture LOC, manually counted edges, etc.) so future fixture edits can update assertions safely.
- The harness adds no new top-level dependencies. It uses only what M01–M17 already pull in.

**Tests:** (the milestone's primary deliverable *is* tests, so this section enumerates the test inventory rather than separate verification cases)

- `tests/integration/test_validation_shell_realistic.py` — two test functions:
  - `test_shell_realistic_baseline_invariants` — the invariants enumerated under deliverables.
  - `test_shell_realistic_with_scope_exclude` — the M17 invariant.
- `tests/integration/test_validation_typescript_realistic.py` — one test function, `test_typescript_realistic_invariants`.
- `tests/integration/test_validation_real_repos.py` — three test functions:
  - `test_tekhton_real_repo_invariants` — gated by `SDI_VALIDATION_TEKHTON`.
  - `test_bifl_tracker_real_repo_invariants` — gated by `SDI_VALIDATION_BIFL`.
  - `test_real_repo_harness_skips_without_env_vars` — fast assertion that the prior two skip cleanly when env vars are absent (a meta-test that prevents the module from accidentally running unguarded against arbitrary directories).
- Fixture READMEs under `tests/fixtures/shell-heavy-realistic/README.md` and `tests/fixtures/typescript-realistic/README.md` — each lists the manually counted edge count and pattern shape distribution that the integration tests assert against. Updating fixtures requires updating the README.
- Optional captured baseline at `tests/integration/fixtures/_baselines/bifl_tracker_pre_m16.json` — produced during M16 implementation by running M16's pre-merge code against the user's bifl-tracker checkout, storing the per-language entropy values, and committing the file. Absence of the file in a fresh checkout causes `test_bifl_tracker_real_repo_invariants` to skip the regression assertion with a warning.

**Watch For:**
- **Real-repo paths must never be hardcoded.** The harness reads `os.environ["SDI_VALIDATION_TEKHTON"]` and `os.environ["SDI_VALIDATION_BIFL"]`. A path literal under `/home/geoff/...` in a test file is a defect — it would fail on every other developer's machine and in CI.
- **The harness writes into the user's real repo.** When `SDI_VALIDATION_TEKHTON` is set, `sdi init` and `sdi snapshot` create `.sdi/` in the user's checkout. The module docstring must call this out loudly. Reviewers may ask whether the harness should run in a temp clone instead — the answer is no for v0 (the dogfooding workflow benefits from snapshots accumulating in the real repo for trend visualization), but document the trade-off.
- **`SDI_VALIDATION_*` env vars must not be required for any default test run.** Verify by running `pytest tests/integration/` with the vars unset and confirming all real-repo tests skip with a non-error status. The "meta-test" `test_real_repo_harness_skips_without_env_vars` enforces this.
- **Fixture floor numbers must be conservative.** If the manual edge count in `shell-heavy-realistic/` is 52 edges, the assertion is `>= 45`, not `== 52`. Exact equality breaks every time the fixture gains or loses a `source` line. The README documents the actual count for human consumption; the test asserts a floor.
- **Per-language assertions key off `pattern_entropy_by_language`.** This field is introduced in M16. If M18 lands before M16, the harness must skip the per-language assertions with a clear `pytest.skip("M16 pattern_entropy_by_language not present yet")`. Do not write fallback paths reading the aggregate — that defeats the purpose of the harness.
- **The TS regression baseline is fragile.** It captures one moment in bifl-tracker's history. Re-capture the baseline whenever bifl-tracker's structure changes materially. The 10% tolerance absorbs minor noise; if the harness fails repeatedly because of legitimate bifl-tracker evolution, update the baseline rather than loosening the tolerance.
- **Bundled fixtures vs real repos serve different purposes.** Bundled fixtures are reproducibility checks; real repos are reality checks. Do not consolidate the two into a single "validation harness" with conditional logic — they should remain separate test files with separate purposes.
- **Snapshots are written into `.sdi/snapshots/` even on bundled fixtures.** The fixture directories will gain `.sdi/` subdirectories during test runs. Add `tests/fixtures/*/.sdi/` to `.gitignore` if not already present, and verify each test cleans up (or relies on a `tmp_path` copy of the fixture) so the committed fixture tree stays clean.
- **The harness is a regression-detection tool, not a metrics tracker.** It does not store historical snapshots, does not compute trends across runs, does not file alerts. SDI's own `sdi trend` is the right tool for that — the harness is a one-shot invariant check.
- **Phrasing audit applies.** `git grep` of M18 deliverables for `\b(robust|ad-hoc|good|bad|best practice|proper|quality|sane|healthy|reasonable)\b` must return zero hits in pattern-related contexts (per the M14 precedent). The PR description must include the grep result.

**Seeds Forward:**
- Closes the dogfooding loop: the next time SDI is exercised against a new language adapter or a new pattern category, M18's harness either passes (no regression) or fails with a specific assertion (clear signal of what regressed).
- Provides a template for future per-language validation milestones (Ruby, Lua, etc.) — each new language gets a `tests/fixtures/<lang>-realistic/` fixture and a corresponding integration test file with the same invariant shape.
- Establishes the env-var opt-in protocol that future real-repo validation may extend (e.g., `SDI_VALIDATION_<REPO>` for any repo a developer wants to dogfood against).
- Marks a natural freeze point for the v0 era: when the harness is green against Tekhton and bifl-tracker, the bifl-tracker validation criterion in `.claude/sdi-rust-scope.md` "Freeze criteria for sdi-py" is structurally satisfied and the era can close.

---
