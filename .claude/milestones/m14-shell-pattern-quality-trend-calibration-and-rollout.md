### Milestone 14: Shell Pattern Quality, Trend Calibration, and Rollout
<!-- milestone-meta
id: "14"
status: "planned"
-->


**Scope:** Improve shell signal quality beyond raw parsing by calibrating pattern extraction, validating trend behavior on shell-heavy histories, and documenting operational guidance so shell support is trustworthy for gates and remediation workflows.

**Deliverables:**
- Pattern quality expansion in `src/sdi/parsing/shell.py` and related pattern handling paths:
  - Refine `error_handling` detection to distinguish robust vs ad-hoc failure handling structures.
  - Add/strengthen detection for `async_patterns` where shell semantics apply (background jobs, `wait`, pipeline fan-out) using explicit structural rules.
  - Improve `data_access` and `logging` captures for common shell toolchains (`curl`, `jq`, `psql`, `mysql`, `logger`, structured `printf` conventions).
  - Preserve measurement-only semantics: counts and hashes only, no value judgments.
- Shell-focused fixture evolution:
  - Add `tests/fixtures/shell-heavy/` with representative script layouts (deployment scripts, CI helpers, ops jobs).
  - Extend `tests/fixtures/evolving/` (or add a dedicated evolving shell fixture) with 4+ scripted commits showing realistic structural drift and stabilization.
- Trend and threshold validation:
  - Add integration tests proving shell changes move divergence deltas as expected across snapshots.
  - Add `sdi check` coverage for shell-driven threshold exceed/within-bound conditions.
  - Verify first shell baseline snapshot returns null deltas, not zero.
- Documentation and DX updates:
  - Update `README.md` quick-start language to explicitly mention shell support and grammar installation path.
  - Update `docs/ci-integration.md` examples to include shell-heavy repositories and optional stricter shell-focused thresholds.
  - Document known limitations (dynamic `source`, heredoc-heavy scripts, generated shell wrappers).
- Performance and cache verification:
  - Ensure parse cache works for shell files and reduces repeated snapshot latency.
  - Add benchmark or targeted perf test proving acceptable runtime on large shell-script sets.

**Acceptance criteria:**
- Shell pattern instances contribute to catalog entropy and velocity in a stable, reproducible way.
- On shell-heavy evolving fixtures, `sdi trend` shows coherent movement across at least 3 snapshots.
- `sdi diff` reflects shell-initiated structural changes in expected dimensions.
- `sdi check` can fail with exit 10 on shell-induced threshold exceed and pass after remediation snapshots.
- Documentation clearly explains how shell support behaves, where it is strong, and where limits remain.
- No regressions to existing Python/TS/JS/Go/Java/Rust pipelines.

**Tests:**
- `tests/unit/test_shell_adapter.py` additions:
  - richer pattern recognition cases for error/logging/data-access/async-like shell structures
  - deduplication and structural-hash stability assertions
- `tests/unit/test_catalog_velocity_spread.py` extensions:
  - shell-origin pattern instances affect velocity/spread as expected
- `tests/integration/test_multi_snapshot.py` or new shell-specific integration:
  - init -> snapshot -> modify shell scripts -> snapshot -> diff -> trend -> check
- `tests/benchmarks/test_parsing_perf.py`:
  - shell-heavy parsing and cache-hit performance case

**Watch For:**
- Overfitting pattern rules to one team's shell style can distort entropy for other repos; keep rules structural and broad.
- Shell scripts often mix generated and handwritten code; recommend explicit excludes for generated wrappers where needed.
- Fish and zsh syntax can diverge from POSIX/bash grammar; document parser coverage boundaries and skip unsupported forms cleanly.
- Threshold defaults tuned for app code may be too strict for script-heavy repos; provide override examples with mandatory expiry.

**Seeds Forward:**
- Makes shell support production-ready for CI gates rather than exploratory.
- Improves remediation usability by turning shell drift into interpretable catalog and trend output.
- Provides a template for adding future language support with two-step rollout: ingestion foundation, then signal calibration.

---
