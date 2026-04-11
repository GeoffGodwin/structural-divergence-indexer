### Milestone 1: Project Skeleton, Config System, and Core Data Structures
<!-- milestone-meta
id: "01"
status: "done"
-->


**Scope:** Establish the project foundation — `pyproject.toml`, package structure, the `sdi` CLI entry point with Click, the complete configuration loading system with five-level precedence, and the core data structures (`FeatureRecord`, `Snapshot`, `DivergenceSummary`) as dataclasses. No analysis logic — this milestone produces a CLI that can load config, print its version, and validate configuration. The `sdi init` command creates the `.sdi/` directory with a default config file.

**Deliverables:**
- `pyproject.toml` with PEP 621 metadata, all dependency declarations, entry point `sdi = "sdi.cli:cli"`, and extras (`[dev]`, `[all]`, `[web]`, `[systems]`)
- `src/sdi/__init__.py` with `__version__`
- `src/sdi/config.py` with full config loading (five-level precedence), validation (including threshold override expiry enforcement), and built-in defaults
- `src/sdi/cli/__init__.py` with root Click group, global flags (`--format`, `--no-color`, `--quiet`, `--verbose`), and top-level exception handler
- `src/sdi/cli/init_cmd.py` with `sdi init` that creates `.sdi/`, writes `config.toml` with commented defaults, and adds `.sdi/cache/` to `.gitignore`
- `src/sdi/snapshot/model.py` with `Snapshot`, `DivergenceSummary`, `FeatureRecord` dataclasses and JSON serialization/deserialization
- `src/sdi/snapshot/storage.py` with atomic file write utility (`write_atomic`) and snapshot read/write/list/retention-enforcement functions
- `tests/conftest.py` with shared fixtures (temporary directories, sample config dicts)
- `tests/unit/test_config.py`
- `tests/unit/test_snapshot_model.py`
- `tests/unit/test_storage.py`
- `.gitignore` with Python defaults + `.sdi/cache/`

**Acceptance criteria:**
- `pip install -e ".[dev]"` succeeds and `sdi --version` prints the version
- `sdi --help` lists all subcommand names (placeholders for unimplemented commands print "not yet implemented" and exit 1)
- `sdi init` creates `.sdi/config.toml` with all default values as comments, creates `.sdi/snapshots/` directory, and adds `.sdi/cache/` to `.gitignore`
- `sdi init --force` overwrites existing `.sdi/config.toml`
- `sdi init` in a non-git directory exits with code 2 and a descriptive error
- Config loading resolves CLI flags > env vars > project config > global config > defaults
- A config with `[thresholds.overrides.X]` missing `expires` exits with code 2
- Malformed TOML exits with code 2 with file path and line number
- `Snapshot` dataclass round-trips through JSON (serialize → deserialize → compare)
- `write_atomic` uses tempfile + `os.replace` — verified by test that simulates crash mid-write
- Snapshot retention enforcement deletes oldest files when count exceeds limit
- All unit tests pass: `pytest tests/unit/test_config.py tests/unit/test_snapshot_model.py tests/unit/test_storage.py`

**Tests:**
- `tests/unit/test_config.py`: Config loading from each precedence level, fallback to defaults, env var override, invalid TOML handling (check exit code 2 and error message), threshold override without `expires` rejected, expired override silently ignored, unknown keys produce deprecation warning
- `tests/unit/test_snapshot_model.py`: `Snapshot` JSON round-trip, `DivergenceSummary` with null deltas (first snapshot case), `snapshot_version` field presence, `FeatureRecord` construction
- `tests/unit/test_storage.py`: Atomic write creates file, atomic write does not produce partial file on simulated failure, snapshot listing sorted by timestamp, retention enforcement deletes oldest when limit exceeded, retention of 0 means unlimited

**Watch For:**
- Python 3.10 lacks `tomllib` in stdlib — must use `tomli` with a conditional import: `try: import tomllib except ImportError: import tomli as tomllib`
- `os.replace()` is atomic on POSIX but may not be on Windows across filesystems — tempfile must be created in the same directory as the target
- Click's `--no-color` flag and the `NO_COLOR` env var need to be wired into Rich's console configuration early — retrofitting is painful
- The top-level exception handler in `cli/__init__.py` must catch `SystemExit` to preserve exit codes while catching everything else as code 1

**Seeds Forward:**
- `config.py` is imported by every subsequent module — its API (`load_config() -> SDIConfig` dataclass) must be stable
- `FeatureRecord` dataclass defined here is the contract between Stage 1 (parsing) and Stages 2–4 — fields must include: `file_path`, `language`, `imports` (list of resolved import targets), `symbols` (list of defined names), `pattern_instances` (list of AST subtree descriptors), `lines_of_code`
- `Snapshot` dataclass must include fields for all four SDI dimensions plus `snapshot_version`, `timestamp`, `commit_sha`, `config_hash` — even though most are populated in later milestones
- `write_atomic()` in `storage.py` will be reused by boundary spec writes and cache writes
- The `sdi init` command will be extended in Milestone 9 to optionally write a starter `boundaries.yaml`

---
