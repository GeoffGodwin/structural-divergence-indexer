### Milestone 14: Shell Pattern Quality, Trend Calibration, and Rollout
<!-- milestone-meta
id: "14"
status: "done"
-->


**Scope:** Improve shell signal quality beyond raw parsing by calibrating pattern extraction, validating trend behavior on shell-heavy histories, and documenting operational guidance so shell support is trustworthy for gates and remediation workflows. Builds directly on M13's `ShellAdapter` and `_shell_patterns.py`; this milestone extends — not replaces — those modules.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 4, SDI never classifies code as "good" or "bad." All language in this milestone uses *measurement* phrasing: "structurally distinct shapes," "additional categories detected," "broader command-name coverage." Phrasing like "robust vs ad-hoc," "best practice," or "quality" must not appear in code, comments, tests, or docs delivered by this milestone.

**Deliverables:**
- Pattern quality expansion in `src/sdi/parsing/_shell_patterns.py` (the walker module introduced in M13). All additions emit `(category, ast_hash, location)` tuples via the existing `_shell_structural_hash` helper, which folds `command_name` into the structural fingerprint so distinct command names produce distinct shapes.
  - **`error_handling` — broaden the M13 set so the following structures each produce a distinct `ast_hash`:**
    - `set` invocations: any flag string containing `e`, `u`, or `o pipefail` (M13 baseline).
    - `trap <handler> <signal>` for any signal in `{ERR, EXIT, INT, TERM, HUP, QUIT}`.
    - `if_statement` whose immediate body contains `exit` or `return` with non-zero literal.
    - `list` (`||` / `&&`) right-hand side ending in `exit`/`return`/`false`.
    - `command` with `command_name == "exit"` or `"return"` and a non-zero numeric literal first argument.
    - `command_substitution` whose result is consumed by `[ -z ... ]` / `[ -n ... ]` / `[[ ... ]]` test expressions (defensive existence checks).
    - **No quality ranking.** Every structurally distinct shape is its own catalog entry; entropy rises with shape count, full stop.
  - **`async_patterns` — extend the existing category to shell-flavoured concurrency. Decision noted explicitly: catalog entropy is per-category, not per-language; mixing shell `&` shapes with Python `async def` shapes in the same category is intentional and consistent with the language-agnostic catalog model.** Detect:
    - Any command terminated by `&` (background job): the parent node is `command` with `background = "&"` field, or a `pipeline` whose final element is followed by `&`.
    - `command_name == "wait"` with or without arguments.
    - `pipeline` nodes with three or more stages (fan-out heuristic): a structural-only count, no semantic judgment.
    - `command_name in {"xargs", "parallel"}` with a `-P` / `--max-procs` flag literal.
  - **`data_access` — populate `command_name` allow-list:**
    - `{curl, wget, jq, yq, psql, mysql, mysqldump, pg_dump, redis-cli, mongo, mongosh, sqlite3, aws, gcloud, kubectl, az, doctl, terraform}`.
    - Detection rule: `command` node whose `command_name` text matches the allow-list. The structural hash includes `command_name` (M13 helper), so `curl` and `psql` are distinct shapes — verify in tests.
  - **`logging` — populate `command_name` allow-list:**
    - `{echo, printf, logger, tee}` (the M13 baseline) plus `>&2` redirection patterns: any `redirected_statement` whose redirect target is `&2`. Treat the redirect form as a separate shape from bare `echo`.
  - **Measurement-only semantics — explicit guard:** any new helper, comment, test name, or docstring containing the words "good," "bad," "best practice," "robust," "ad-hoc," "proper," or "quality" is a defect. The PR description must affirm this audit was performed.
- Shell-focused fixture evolution:
  - Add `tests/fixtures/shell-heavy/` with **8–12 scripts (≈20–60 LOC each)** spanning three subdirectories: `deploy/` (3-4 scripts), `ci/` (3-4 scripts), `ops/` (2-4 scripts). Aggregate content guarantees:
    - **≥ 4 distinct `error_handling` shapes** (e.g., `set -euo pipefail`, `trap ... ERR`, `cmd || exit 1`, `if ! foo; then return 1; fi`).
    - **≥ 3 distinct `data_access` shapes** (e.g., `curl`, `psql`, `kubectl`).
    - **≥ 2 distinct `logging` shapes** (e.g., `echo`, `>&2` redirect).
    - **≥ 2 distinct `async_patterns` shapes** (e.g., backgrounded `&`, `wait`, `xargs -P`).
    - **≥ 2 cross-script `source` imports** to exercise the graph builder.
  - Add `tests/fixtures/evolving-shell/` as a **new dedicated fixture** (do not modify the existing `tests/fixtures/evolving/` Python fixture). Include a `setup_fixture.py` that materializes 4 commits in a temp git repo:
    - **C1 (baseline):** 5 shell scripts, 1 `error_handling` shape (`set -e` only), 1 `logging` shape, no `async_patterns`.
    - **C2 (drift):** add 2 new `error_handling` shapes (`trap ... ERR`, `cmd || exit 1`) and 1 new `logging` shape (`>&2` redirect). Net new shapes: 3.
    - **C3 (consolidation):** refactor C2's three error_handling shapes down to two by replacing all `cmd || exit 1` instances with `set -euo pipefail` at file head. Net shape change: −1.
    - **C4 (regression):** introduce a 4th `error_handling` shape and a new `async_patterns` shape (`xargs -P 4`). Net new shapes: 2.
  - Mirror M13's `simple-shell/` style for file conventions (extension `.sh`, exec bit set on entrypoint scripts, shebangs `#!/usr/bin/env bash`).
- Trend and threshold validation — add `tests/integration/test_shell_evolving.py` (gated by `requires_shell_adapter`) that runs `setup_fixture.py` and walks C1→C4, asserting:
  - **C1 snapshot:** `divergence.pattern_entropy_delta is None` (first snapshot baseline). All four delta dimensions are `None`, not `0`.
  - **C1→C2 (`sdi diff`):** `pattern_entropy_delta["error_handling"] >= 2`, `pattern_entropy_delta["logging"] >= 1`, `convention_drift_rate > 0` (net new shapes).
  - **C2→C3 (`sdi diff`):** `pattern_entropy_delta["error_handling"] <= -1`, `convention_drift_rate < 0` (consolidation — old shapes lost).
  - **C3→C4 (`sdi diff`):** `pattern_entropy_delta["error_handling"] >= 1`, `pattern_entropy_delta["async_patterns"] >= 1`.
  - **`sdi trend`** across all four snapshots returns a 4-point series with the correct sign sequence: `[null, +, -, +]` for `convention_drift_rate`.
  - **`sdi check` exit codes:** with default thresholds, C1→C2 exits `10` (threshold exceeded — drift rate > `3.0`); C2→C3 exits `0`; C3→C4 exits `0` (within bounds with default thresholds, since 2 new shapes < `3.0`).
  - All numeric thresholds above use the defaults from `src/sdi/config.py`. If those defaults change, update assertions accordingly — do not hardcode numbers that drift from config.
- Documentation and DX updates — concrete content checklist:
  - **`README.md`** — under the existing language-support section, add a "Shell" subsection covering:
    1. Supported extensions: `.sh, .bash, .zsh, .ksh, .dash, .ash`. Note `.fish` is not supported.
    2. Shebang detection: extensionless executable files with `#!/usr/bin/env bash` (and the allow-list from M13) are picked up automatically.
    3. Installation: `pip install 'sdi[all]'` includes `tree-sitter-bash`.
    4. Categories detected for shell: `error_handling`, `logging`, `data_access`, `async_patterns` (with one-line descriptions matching `categories.py`).
    5. Known limits: dynamic `source` paths skipped, heredoc bodies not pattern-matched, fish syntax unsupported, parse failures emit a per-file warning and skip.
  - **`docs/ci-integration.md`** — add:
    1. A worked example invoking `sdi check` against a shell-heavy repo.
    2. A concrete TOML override block for shell-script-heavy projects:
       ```toml
       [thresholds.overrides.error_handling]
       pattern_entropy_rate = 6.0
       expires = "2026-Q4"
       reason = "Migrating ops scripts from set -e to explicit error traps"

       [thresholds.overrides.async_patterns]
       pattern_entropy_rate = 5.0
       expires = "2026-12-31"
       reason = "Pipeline parallelism rollout in deploy/"
       ```
    3. A note that default thresholds tuned for application code may be too strict for script-heavy repos and overrides are the supported relief valve.
  - **`CHANGELOG.md`** — entry under "Unreleased": `Added: shell pattern quality (broader error_handling, async_patterns, data_access, logging coverage), shell-heavy fixtures, and CI integration docs.`
- Performance and cache verification:
  - Add a unit test in `tests/unit/test_parse_cache.py` (or new `test_parse_cache_shell.py`) verifying: parse a shell file once → write cache; parse the same bytes → read returns the cached `FeatureRecord` (assert no parser invocation by mocking `_get_parser` or by timing). No `_parse_cache.py` source changes expected — this confirms language-agnostic behaviour holds for shell.
  - Add a benchmark case to `tests/benchmarks/test_parsing_perf.py` parameterised on `language="shell"` that:
    - Generates 100 synthetic shell scripts of ≈50 LOC each in a temp dir.
    - Asserts cold-parse runtime < **1.5s** on a 4-core CI runner (`SDI_WORKERS=4`).
    - Asserts cache-hit rerun < **0.3s** on the same set.
    - Numbers are budgets, not contracts: tune once the benchmark runs locally, but the budget must be hard-coded so regressions surface.

**Acceptance criteria:**
- Shell pattern instances appear in `PatternCatalog` for all four categories (`error_handling`, `logging`, `data_access`, `async_patterns`) when present in source. Identical bytes parsed twice produce identical `ast_hash` sets (reproducibility).
- `sdi trend` on `tests/fixtures/evolving-shell/` (4 commits) returns 4 data points; the `convention_drift_rate` series follows the sign sequence `[null, +, -, +]`.
- `sdi diff` between any two `evolving-shell` commits returns the deltas enumerated in the trend/threshold validation section above (numeric assertions, not "as expected").
- `sdi check` exits `10` for the C1→C2 transition and `0` for C2→C3 and C3→C4 with default thresholds.
- Documentation acceptance is checklist-based, not subjective: `README.md` includes the 5 enumerated items in the docs-update section; `docs/ci-integration.md` includes the worked example and the literal TOML override snippet; `CHANGELOG.md` has the new entry.
- Benchmark assertions pass: cold parse < 1.5s, cache rerun < 0.3s on 100×50-LOC synthetic shell scripts.
- **No regressions:** existing fixture-based tests for Python/TS/JS/Go/Java/Rust produce byte-identical `language_breakdown` and `pattern_catalog` keys (excluding new shell entries) compared to a pre-M14 reference run. Capture the reference by running the suite before any M14 changes; commit the reference JSON if needed for diffing.
- **Philosophy compliance:** grep of all M14 deliverables (source, tests, docs) returns zero hits for `\b(robust|ad-hoc|good|bad|best practice|proper|quality)\b` in pattern-related contexts. The PR description must include the grep result.

**Tests:** (gate every shell-touching test with `requires_shell_adapter` from `tests/conftest.py`)

- `tests/unit/test_shell_adapter.py` — extend with:
  - one case per new `error_handling` shape from the deliverables list (5 cases beyond M13's 4); each asserts a unique `ast_hash`.
  - one case per `async_patterns` rule (background `&`, `wait`, fan-out pipeline, `xargs -P`).
  - one case asserting `data_access` allow-list covers `curl`, `psql`, `kubectl`, `jq` with distinct `ast_hash` per command.
  - one case for `logging` `>&2` redirect producing a different `ast_hash` than bare `echo`.
  - reproducibility: parsing the `tests/fixtures/shell-heavy/` tree twice yields identical `(category, ast_hash)` multisets.
- `tests/unit/test_catalog_velocity_spread.py` — extend with two cases:
  - **velocity:** building a catalog from `evolving-shell` C2 with C1 as `prev_catalog` produces `velocity[shape] == 1` for each newly introduced shell shape and `velocity[shape] == 0` for unchanged shapes.
  - **boundary spread:** when the same shell `error_handling` shape appears in two different Leiden clusters of the `shell-heavy` fixture, `boundary_spread[shape] == 2`.
- `tests/integration/test_shell_evolving.py` — new file (referenced in deliverables) running the full `init → snapshot×4 → diff → trend → check` workflow against `evolving-shell`. Assertions enumerated in the trend/threshold validation deliverable.
- `tests/benchmarks/test_parsing_perf.py` — new `test_shell_parse_perf_cold` and `test_shell_parse_perf_cached` cases with the budgets above.

**Watch For:**
- **Phrasing audit is enforced.** "Robust vs ad-hoc," "best practice," "good/bad" phrasing in any deliverable file violates Non-Negotiable Rule 4. The PR must include `git grep -nE '\b(robust|ad-hoc|good|bad|best practice|proper|quality)\b' src/ tests/ docs/ README.md CHANGELOG.md` output showing zero pattern-related hits.
- **`async_patterns` mixing across languages is intentional.** The same category aggregates Python `async def` and shell `&` shapes. Reviewers may flag this as a smell; the milestone explicitly endorses it. Do not split the category to "fix" the perceived overlap — that would break the language-agnostic catalog model.
- **`command_name` must be folded into the structural hash for `command` nodes.** This is the M13 helper `_shell_structural_hash`; without it, `curl`, `psql`, and `kubectl` collapse to one shape and `data_access` entropy becomes meaningless. Verify each new test case asserts distinct hashes between distinct command names.
- **Overfitting risk.** Detection rules are structural and command-name-based — never path-based, file-name-based, or content-keyword-based. Rules that key off `deploy.sh` or `# CI script` belong elsewhere.
- **Generated shell wrappers** (e.g., autotools, hand-rolled codegen output) inflate entropy and convention drift. Document in `README.md` that users should add such directories to `[core] exclude` patterns; do not attempt auto-detection in v1.
- **Fish/zsh edge cases.** `tree-sitter-bash` parses POSIX/bash cleanly; zsh-specific constructs (e.g., `=()` process substitution syntax variants) may produce ERROR nodes. The adapter already returns `None` on parse exceptions via `parse_file_safe`; do not add zsh-specific handling.
- **Threshold defaults vs. script-heavy repos.** The override examples in `ci-integration.md` are the only sanctioned relief mechanism — never lower default thresholds to accommodate scripts.
- **Benchmark numbers are CI-runner dependent.** The 1.5s / 0.3s budgets target a 4-core x86_64 GitHub-Actions-class runner. If running on slower hardware, document the local baseline in the PR description but keep the committed budget at the stated values.

**Seeds Forward:**
- Makes shell support production-ready for CI gates rather than exploratory.
- Improves remediation usability by turning shell drift into interpretable catalog and trend output.
- Provides a template for adding future language support with two-step rollout: ingestion foundation, then signal calibration.

---
