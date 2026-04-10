### Milestone 12: Packaging, Distribution, and Documentation

**Scope:** Prepare SDI for public release: finalize `pyproject.toml` for PyPI, create the Homebrew formula, write the README with quick start guide, finalize CI integration documentation, and ensure clean installation on all supported platforms. This is the release milestone.

**Deliverables:**
- `pyproject.toml` finalized: metadata, classifiers, URLs, entry points, extras
- PyPI-ready package: `python -m build` produces correct wheel and sdist
- Homebrew formula in a `homebrew-sdi` tap structure (can be a separate repo or documented)
- `README.md`: project description, badges, quick start (install → init → snapshot → diff in 30 seconds), feature overview, comparison to existing tools, contributing guidelines
- `LICENSE` file (MIT or Apache 2.0)
- `docs/ci-integration.md` finalized: GitHub Actions, GitLab CI, generic CI with copy-pasteable snippets
- Tab completion installation instructions in README
- Changelog (CHANGELOG.md) with initial release entry
- `sdi --version` output is correct and matches package version

**Files to create or modify:**
- `pyproject.toml` (finalize)
- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `docs/ci-integration.md` (finalize)
- `src/sdi/__init__.py` (version bump to 0.1.0)

**Acceptance criteria:**
- `pip install .` in a fresh virtualenv succeeds and `sdi --version` works
- `pip install ".[all]"` installs all language grammars
- `python -m build` produces a wheel and sdist without errors
- `twine check dist/*` passes
- README quick start works end-to-end: clone fixture repo, `pip install sdi`, `sdi init`, `sdi snapshot`, `sdi show`
- Tab completion instructions work for bash and zsh
- CI integration examples in docs are copy-pasteable and correct
- `sdi` on a repository with no configuration produces useful output (zero-config principle)
- Package metadata (description, URLs, classifiers) is correct on PyPI test instance

**Tests:**
- Installation test: `pip install .` in a clean virtualenv, run `sdi --version`
- Build test: `python -m build` succeeds, `twine check dist/*` passes
- README quick start: follow the documented steps on a fresh fixture, verify it works
- Zero-config test: `sdi snapshot` on an un-initialized repo with Python files produces a valid snapshot

**Watch For:**
- `pyproject.toml` entry points must use the correct module path: `[project.scripts] sdi = "sdi.cli:main"` (or wherever the Click group is defined).
- Tree-sitter grammar packages may not have wheels for all platforms. Document which grammars require compilation and what build tools are needed.
- Homebrew formula for Python packages requires careful handling of virtualenv isolation. Study existing Python formula patterns in Homebrew.
- The `sdi` package name may be taken on PyPI. Check availability and have a fallback (e.g., `sdi-tool`, `structural-divergence-indexer`).
- Version string must come from a single source of truth. Use `importlib.metadata` in `__init__.py` or a `__version__` that `pyproject.toml` also reads.

**Seeds Forward:**
- This is v0.1.0. Post-release priorities are: collecting early adopter feedback, resolving open design questions (weighted edges, gamma auto-tuning, YAML library), and planning the v1.0 stability release.
