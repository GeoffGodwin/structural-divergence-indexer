### Milestone 11: Testing, Fixtures, and Quality Gate

**Scope:** Build out the complete test suite: unit test coverage to 80%+, all integration tests, the evolving fixture repo (built by setup script), and CI quality gates. This milestone ensures the test infrastructure is comprehensive enough that future changes can be validated automatically.

**Deliverables:**
- Complete unit test coverage across all modules (80%+ target)
- `tests/fixtures/evolving/` fixture: a git repo built by a setup script with multiple commits introducing progressive structural drift
- Integration tests: full lifecycle (`init` → `snapshot` → modify → `snapshot` → `diff` → `trend` → `check`)
- CLI output snapshot tests: capture stdout/stderr for each command and compare against expected output
- Coverage reporting via pytest-cov, integrated into CI
- CI workflow runs: lint (ruff or flake8), type check (mypy), unit tests, integration tests, coverage report
- Test documentation: what each fixture is for, how to regenerate evolving fixture

**Files to create or modify:**
- `tests/fixtures/evolving/setup_fixture.py` (script to build git history)
- `tests/integration/test_full_pipeline.py` (expand)
- `tests/integration/test_multi_snapshot.py` (expand)
- `tests/integration/test_cli_output.py` (expand)
- All `tests/unit/test_*.py` files (fill coverage gaps)
- `.github/workflows/ci.yml` (update with full pipeline)
- `pyproject.toml` (add ruff/mypy config)

**Acceptance criteria:**
- `pytest tests/unit/ --cov=sdi --cov-report=term` shows 80%+ coverage
- All integration tests pass on Linux and macOS
- `tests/fixtures/evolving/setup_fixture.py` creates a git repo with 5+ commits showing progressive drift
- CI runs: ruff lint, mypy type check, pytest unit, pytest integration, coverage upload
- No test depends on external network access
- No test depends on a specific timezone
- All tests run in under 2 minutes total on a modern machine
- Fixture repos are self-contained (no external dependencies)

**Tests:**
- Coverage gap analysis: run coverage, identify untested code paths, add tests
- `tests/fixtures/evolving/setup_fixture.py` creates a fixture that, when analyzed with `sdi trend`, shows a clear trajectory of increasing pattern entropy over 5 commits
- Edge case tests: empty repos, single-file repos, repos with only unsupported languages, repos with corrupt git history, repos with binary files

**Watch For:**
- The evolving fixture setup script must create reproducible git history (deterministic commit timestamps and content).
- Integration tests that spawn `sdi` as a subprocess must handle PATH correctly (the dev install must be on PATH).
- CLI output snapshot tests are fragile if output includes timestamps or paths. Normalize these in test comparisons.
- mypy configuration should use `strict = false` initially but enable `disallow_untyped_defs = true` for the `sdi/` package.

**Seeds Forward:**
- The test suite is the safety net for the v1 release (Milestone 12).
- Coverage reports establish the quality bar for future contributions.
- The evolving fixture is the canonical test case for demonstrating SDI's value proposition.

---
