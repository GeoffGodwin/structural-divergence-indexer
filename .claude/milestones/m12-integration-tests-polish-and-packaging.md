### Milestone 12: Integration Tests, Polish, and Packaging

**Scope:** Comprehensive integration testing (multi-snapshot lifecycle, evolving fixture), the `evolving` test fixture with progressive drift across git commits, end-to-end verification of all CLI commands, CI workflow files (`.github/workflows/ci.yml`), and final packaging verification (wheel build, entry point, extras).

**Deliverables:**
- `tests/fixtures/evolving/` — a git repository fixture with 5+ commits that introduce progressive structural drift (built by `tests/fixtures/setup_fixture.py` script)
- `tests/integration/test_multi_snapshot.py` — full lifecycle: init → snapshot → modify → snapshot → diff → trend → check
- `tests/integration/test_full_pipeline.py` — expanded to cover all fixture types
- `tests/integration/test_cli_output.py` — expanded to cover all commands with all output formats
- `.github/workflows/ci.yml` — lint (ruff), type check (mypy), unit tests, integration tests, coverage report
- `.github/workflows/benchmarks.yml` — performance benchmarks triggered on release tags
- Final `pyproject.toml` verification: wheel builds correctly, `sdi` entry point works from a clean install, all extras install correctly

**Acceptance criteria:**
- `tests/fixtures/setup_fixture.py` creates the evolving fixture reproducibly (creates a temp git repo with scripted commits)
- Multi-snapshot lifecycle test passes: init → snapshot → modify fixture (add a new pattern variant) → snapshot → diff (shows correct delta) → trend (shows two data points) → check (threshold comparison)
- All CLI commands produce valid output in all formats (text, json, csv where applicable)
- All exit codes match their documented semantics (0, 1, 2, 3, 10)
- CI workflow runs lint + type check + unit tests + integration tests on push/PR
- Benchmark workflow runs on release tags only
- `python -m build` produces a valid wheel and sdist
- `twine check dist/*` passes
- Coverage report shows ≥ 80% unit test coverage
- All tests pass on Python 3.10, 3.11, and 3.12

**Tests:**
- `tests/integration/test_multi_snapshot.py`: Full lifecycle on evolving fixture — init, snapshot (baseline with null deltas), modify fixture, snapshot (deltas computed), diff (shows changes), trend (two-point series), check (with tight thresholds to trigger exit 10, with relaxed thresholds to pass)
- `tests/integration/test_full_pipeline.py`: Run full pipeline on simple-python, multi-language, and high-entropy fixtures — verify output structure and values
- `tests/integration/test_cli_output.py`: Every command with `--format text`, `--format json`; `sdi trend` with `--format csv`; verify stderr has no data leakage

**Watch For:**
- The evolving fixture requires a real git repository — use `subprocess` to run `git init`, `git add`, `git commit` in a temp directory. Clean up after test run.
- Python version matrix (3.10, 3.11, 3.12) may surface issues with `tomllib` availability (3.10 needs `tomli`), type hint syntax differences, or tree-sitter API changes
- Coverage threshold of 80% unit test coverage — if this is hard to hit, focus coverage on the delta computation, config validation, and pattern fingerprinting modules (highest bug risk)
- mypy with `disallow_untyped_defs = true` will require type annotations on all public functions — ensure this has been maintained throughout all milestones

**Seeds Forward:**
- This milestone produces a shippable v0.1.0 — the complete SDI tool ready for early adopter feedback
- The CI workflow becomes the ongoing quality gate for all future development
- The evolving fixture becomes the canonical test for trend computation accuracy
