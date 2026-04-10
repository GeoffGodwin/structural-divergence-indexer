### Milestone 1: Project Skeleton and Core Infrastructure

**Scope:** Set up the Python package structure, build system, CLI entry point, configuration loading, and basic project infrastructure. This milestone establishes the foundation that every subsequent milestone builds on. No analysis logic — just the skeleton, config system, and a working `sdi --version` command.

**Deliverables:**
- `pyproject.toml` with all dependencies, entry point, and extras (`[all]`, `[web]`, `[systems]`, `[dev]`)
- `src/sdi/__init__.py` with `__version__`
- `src/sdi/config.py` with full config loading (precedence chain, defaults, validation, env var support)
- `src/sdi/cli/__init__.py` with Click group and `--version`, `--no-color`, `--quiet`, `--verbose` global flags
- `src/sdi/cli/init_cmd.py` stub that creates `.sdi/` directory structure and writes default `config.toml`
- `.gitignore` with Python defaults and `.sdi/cache/`
- `tests/conftest.py` with shared fixtures (temp directory, mock repo)
- CI workflow file `.github/workflows/ci.yml`

**Files to create or modify:**
- `pyproject.toml`
- `src/sdi/__init__.py`
- `src/sdi/config.py`
- `src/sdi/cli/__init__.py`
- `src/sdi/cli/init_cmd.py`
- `.gitignore`
- `.github/workflows/ci.yml`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/unit/__init__.py`
- `tests/unit/test_config.py`

**Acceptance criteria:**
- `pip install -e ".[dev]"` succeeds
- `sdi --version` prints the version and exits 0
- `sdi --help` lists all planned subcommands (stubs that print "not yet implemented")
- `sdi init` creates `.sdi/config.toml` with commented defaults and `.sdi/snapshots/` directory
- `sdi init` adds `.sdi/cache/` to `.gitignore` (creating or appending)
- `sdi init --force` overwrites existing `.sdi/config.toml`
- Config loading respects all five precedence levels (CLI > env > project > global > defaults)
- Running `sdi init` outside a git repo exits with code 2 and descriptive error
- Malformed `.sdi/config.toml` exits with code 2 with file path and line number in error message
- `NO_COLOR=1 sdi --version` produces uncolored output
- `pytest tests/unit/test_config.py` passes

**Tests:**
- `tests/unit/test_config.py`:
  - Test built-in defaults are complete (every config key has a default)
  - Test project-local config overrides defaults
  - Test global config at `~/.config/sdi/config.toml` is loaded when project-local is missing
  - Test env vars override file config (`SDI_LOG_LEVEL`, `SDI_WORKERS`)
  - Test `SDI_CONFIG_PATH` overrides discovery
  - Test malformed TOML produces exit code 2 with line number in error
  - Test unknown config keys are silently ignored (forward compatibility)
  - Test `NO_COLOR` env var is respected

**Watch For:**
- `tomllib` is only available in Python 3.11+. For 3.10 support, use `tomli` as a fallback: `try: import tomllib except ImportError: import tomli as tomllib`.
- Click's `--no-color` handling interacts with Rich. Ensure the global `--no-color` flag propagates to the Rich console instance.
- Config validation must report the specific key and expected type on error, not just "invalid config."
- The `.sdi/cache/` gitignore entry must be appended non-destructively to existing `.gitignore` files.

**Seeds Forward:**
- `config.py` is the shared dependency for every module. The `load_config()` function signature and return type (a dataclass or typed dict) must be stable — all later milestones import it.
- The Click group in `cli/__init__.py` defines global options (`--format`, `--no-color`, `--quiet`, `--verbose`) that all subcommands inherit. Establish the Click context passing pattern here.
- `sdi init` creates the directory structure (`.sdi/`, `.sdi/snapshots/`, `.sdi/cache/`) that Milestones 3, 4, and 5 depend on.
- The exit code constants (0, 1, 2, 3, 10) should be defined in a shared location (e.g., `src/sdi/__init__.py` or `src/sdi/exitcodes.py`) for use by all commands.

---
