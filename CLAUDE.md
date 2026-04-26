# Structural Divergence Indexer (SDI)

## Project Identity

SDI (Structural Divergence Indexer) is a CLI tool that computes and tracks the Structural Divergence Index — a composite metric measuring the rate of structural drift in a codebase across four dimensions: pattern entropy, convention drift rate, coupling topology delta, and boundary violation velocity. It captures periodic structural fingerprints (snapshots) via tree-sitter AST parsing and Leiden community detection, diffs them over time, and produces trend data and actionable CI gate checks. Target users are software engineers, tech leads, and engineering managers responsible for the structural health of codebases — particularly teams using AI-assisted development at scale where multiple contributors generate code concurrently without shared structural awareness.

**Languages:**
- Python

**Tech stack:** Python 3.10+, tree-sitter (multi-language AST parsing), leidenalg (Leiden community detection), igraph (graph analysis), Click (CLI framework), Rich (terminal formatting), TOML (configuration), YAML via ruamel.yaml (boundary specs), JSON (snapshots).

**Key dependencies:**

| Package | Purpose |
|---|---|
| tree-sitter >=0.24 | Multi-language AST parsing |
| tree-sitter-python, tree-sitter-javascript, tree-sitter-typescript, tree-sitter-go, tree-sitter-java, tree-sitter-rust | Per-language grammar packages |
| leidenalg | Leiden community detection algorithm |
| igraph | Graph construction, analysis, cycle detection, centrality |
| click | CLI framework (argument parsing, subcommands, help) |
| rich | Terminal output formatting (tables, progress bars, color) |
| tomli / tomllib | TOML config parsing (tomllib is stdlib in 3.11+, tomli for 3.10) |
| tomli-w | TOML writing for `sdi init` config generation |
| ruamel.yaml | YAML parsing for boundary specs (preserves comments) |

**Platform:** Linux (primary), macOS (tested in CI), Windows (best-effort). Distributed via PyPI (`pip install sdi`) and Homebrew (`brew tap geoffgodwin/sdi && brew install sdi`).

**License:** Open source under MIT or Apache 2.0.

## Version Naming

SDI uses **MAJOR.MILESTONE.PATCH** semantic versioning where each position maps to a unit of work the project produces:

- **MAJOR** = the design era. Increments when a new DESIGN document is ratified. Each design lives at `.tekhton/DESIGN_v<N>.md`. Authoritative spec for the v0 era is `.tekhton/DESIGN.md` (the original); for v1 onward it is `.tekhton/DESIGN_v<N>.md`.
- **MILESTONE** = the position of the milestone within the current MAJOR — `1` for the first milestone shipped in the era, `2` for the second, etc. **The counter starts over at every MAJOR bump.** Versions within a MAJOR are dense (no gaps).
- **PATCH** = bugfix, drift fix, or ad-hoc / human-note work against a shipped milestone. Resets to 0 on every new MILESTONE.

Milestone files under `.claude/milestones/` (`m01-*.md`, `m02-*.md`, …) follow the same per-era numbering. At each MAJOR cut, the previous era's milestone files are retired (archived in `MILESTONE_ARCHIVE.md`, removed from the active directory) and the new era starts fresh at `m01-*.md`. The MILESTONE position in the version equals the milestone file number, always.

**Era boundaries:**

| Era | Versions | Design | Status |
|---|---|---|---|
| v0 | `0.1.0`–`0.14.x` | `.tekhton/DESIGN.md` | 14 milestones shipped (`m01`…`m14`); closed for new milestones; files retired at the `1.0.0` cut |
| v1 | `1.0.0`, `1.1.0`, `1.2.0`, … | `.tekhton/DESIGN_v1.md` | First v1 milestone is the new `m01-*.md` → `1.1.0`; cuts `1.0.0` at completion of lifecycle PR |
| v2 | `2.0.0`+ | future | DESIGN_v2.md not yet authored |

Throughout this document and others in the repo, references to "v1" / "v2" / "v3" written before the rename mean the *old* labels — those have been migrated. **The current convention:** "v0" is the past/scaffold era, "v1" is what we are building toward, "v2" is future companion-surface work. See `.tekhton/DESIGN_v1.md` §12 for full versioning policy.

## Architecture Philosophy

### Core Principles

- **Measurement over opinion.** Every claim SDI makes about a codebase is backed by a concrete, reproducible measurement derived from AST analysis or dependency graph structure. No heuristics that cannot be explained. No scores without traceable inputs. If a metric cannot be decomposed into its constituent measurements, it does not ship.
- **Fever chart, not thermometer.** Every metric must be trackable over time. The primary output is always the trend — the rate of change of structural coherence, not the absolute state. Alerts fire on rate-of-change thresholds, not absolute values.
- **Automated inference, human ratification.** SDI infers structural boundaries via community detection, proposes them, and waits for a human to ratify. The tool measures divergence from declared intent, not from its own opinions. Pattern categories detect structural shapes and count them but never classify code as "good" or "bad."
- **Safe defaults, zero mandatory config.** Running `sdi snapshot` on an un-initialized repository produces useful output using purely inferred boundaries. Configuration refines and ratifies — it is never required for first use.
- **Composable Unix tooling.** Reads from filesystem and git history, writes JSON/text to stdout/files, exits with meaningful codes. No daemon, no server, no interactive TUI in v0 (the scaffold era; rule persists into v1 and beyond). Composes with `jq`, `diff`, CI pipelines, and git hooks.
- **Language-agnostic core, language-specific adapters.** The dependency graph, community detection, pattern fingerprinting, and snapshot diffing are language-agnostic. Language specifics live in adapter modules. Tree-sitter provides consistent AST representation across all supported languages.
- **Deterministic and reproducible.** Same commit + same config + same boundaries = same snapshot. Leiden is seeded from previous partition for stability; cold starts use a fixed random seed (default: 42).

### Banned Anti-Patterns

| Anti-Pattern | Enforcement |
|---|---|
| ML/LLM calls in the analysis pipeline | Code review gate. SDI is a measurement instrument; determinism and reproducibility are non-negotiable. |
| Network calls during analysis | No telemetry, no update checks, no remote lookups during analysis. All data is local filesystem and git. |
| Opinions about code quality | SDI never classifies code as "good" or "bad." Pattern entropy is a measurement, not a judgment. |
| Automatic alert suppression | SDI never decides elevated metrics are acceptable. Teams declare intent via threshold overrides with expiry dates. |
| Interactive TUI or daemon mode | CLI invocation only. Unix philosophy — run, produce output, exit. |

### Data Flow

```
Source Files → [Stage 1: tree-sitter parsing] → Per-file feature records
    → [Stage 2: Dependency graph construction] → igraph Graph
    → [Stage 3: Leiden community detection] → Cluster assignments + stability
    → [Stage 4: Pattern fingerprinting] → Pattern catalog + entropy
    → [Stage 5: Snapshot assembly + delta] → Snapshot JSON + human summary
```

Each stage is sequential. Stage 1 is parallelized across files via `ProcessPoolExecutor`. Stages 2–5 are single-threaded. All stages feed forward — no backward dependencies within a single pipeline run.

### Module Boundaries and Dependency Rules

- `sdi/cli/` depends on all other modules (it is the composition root)
- `sdi/parsing/` depends only on tree-sitter and the filesystem — no dependency on graph, detection, or patterns
- `sdi/graph/` depends on `sdi/parsing/` output (feature records) and igraph
- `sdi/detection/` depends on `sdi/graph/` output and leidenalg
- `sdi/patterns/` depends on `sdi/parsing/` output — NOT on graph or detection
- `sdi/snapshot/` depends on outputs from graph, detection, and patterns (assembly point)
- `sdi/config.py` is a leaf dependency — depended on by all modules, depends on none

**Rule:** No module may import from `sdi/cli/`. No circular imports between the core modules. The `config` module is the only shared dependency across all modules.

## Repository Layout

```
sdi/
├── pyproject.toml                    # PEP 621 project metadata, dependencies, entry points
├── README.md                         # Project overview, quick start, badges
├── LICENSE                           # MIT or Apache 2.0 license file
├── CLAUDE.md                         # This file — authoritative development rulebook
├── DESIGN.md                         # Design document (reference, not implementation guide)
├── .gitignore                        # Python defaults + .sdi/cache/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint, test, coverage on push/PR
│       └── benchmarks.yml            # Performance benchmarks on release tags
├── src/
│   └── sdi/
│       ├── __init__.py               # Package version (__version__)
│       ├── cli/
│       │   ├── __init__.py           # Click group definition (root `sdi` command)
│       │   ├── init_cmd.py           # `sdi init` command
│       │   ├── snapshot_cmd.py       # `sdi snapshot` command
│       │   ├── diff_cmd.py           # `sdi diff` command
│       │   ├── trend_cmd.py          # `sdi trend` command
│       │   ├── check_cmd.py          # `sdi check` command
│       │   ├── show_cmd.py           # `sdi show` command
│       │   ├── boundaries_cmd.py     # `sdi boundaries` command
│       │   └── catalog_cmd.py        # `sdi catalog` command
│       ├── config.py                 # Config loading, precedence, defaults, validation
│       ├── parsing/
│       │   ├── __init__.py           # Public API: parse_repository(), FeatureRecord
│       │   ├── discovery.py          # File discovery, .gitignore filtering, language detection
│       │   ├── base.py               # Base language adapter interface
│       │   ├── python.py             # Python tree-sitter adapter
│       │   ├── typescript.py         # TypeScript tree-sitter adapter
│       │   ├── javascript.py         # JavaScript tree-sitter adapter
│       │   ├── go.py                 # Go tree-sitter adapter
│       │   ├── java.py               # Java tree-sitter adapter
│       │   └── rust.py               # Rust tree-sitter adapter
│       ├── graph/
│       │   ├── __init__.py           # Public API: build_dependency_graph()
│       │   ├── builder.py            # Dependency graph construction from feature records
│       │   └── metrics.py            # Graph metrics: density, cycles, hubs, components
│       ├── detection/
│       │   ├── __init__.py           # Public API: detect_communities()
│       │   ├── leiden.py             # Leiden algorithm wrapper, seeding, stability scoring
│       │   └── boundaries.py         # BoundarySpec parsing, ratification, intent divergence
│       ├── patterns/
│       │   ├── __init__.py           # Public API: build_pattern_catalog()
│       │   ├── fingerprint.py        # PatternFingerprint, structural hashing
│       │   ├── catalog.py            # PatternCatalog, category management, canonical marking
│       │   └── categories.py         # Built-in category definitions + tree-sitter queries
│       └── snapshot/
│           ├── __init__.py           # Public API: capture_snapshot(), compute_delta()
│           ├── model.py              # Snapshot dataclass, DivergenceSummary dataclass
│           ├── assembly.py           # Snapshot assembly from pipeline stage outputs
│           ├── delta.py              # Delta computation between two snapshots
│           ├── storage.py            # Snapshot read/write, retention enforcement, atomic writes
│           └── trend.py              # Trend computation across multiple snapshots
├── tests/
│   ├── conftest.py                   # Shared fixtures, test helpers
│   ├── unit/
│   │   ├── test_config.py            # Config loading, precedence, validation
│   │   ├── test_discovery.py         # File discovery, language detection
│   │   ├── test_graph_builder.py     # Dependency graph construction
│   │   ├── test_graph_metrics.py     # Graph metric computation
│   │   ├── test_leiden.py            # Leiden partition stability, seeding
│   │   ├── test_boundaries.py        # Boundary spec parsing, validation
│   │   ├── test_fingerprint.py       # Pattern fingerprinting correctness
│   │   ├── test_catalog.py           # Pattern catalog operations
│   │   ├── test_snapshot_model.py    # Snapshot dataclass serialization
│   │   ├── test_delta.py             # Delta computation
│   │   ├── test_storage.py           # Atomic writes, retention
│   │   └── test_trend.py             # Trend computation
│   ├── integration/
│   │   ├── test_full_pipeline.py     # End-to-end snapshot capture
│   │   ├── test_multi_snapshot.py    # init → snapshot → modify → snapshot → diff → trend
│   │   ├── test_cli_output.py        # CLI stdout/stderr output verification
│   │   └── test_git_hooks.py         # Hook installation and execution
│   ├── fixtures/
│   │   ├── simple-python/            # Small Python project with known structure
│   │   ├── multi-language/           # Python + TypeScript cross-language fixture
│   │   ├── high-entropy/             # Deliberately high pattern variance
│   │   └── evolving/                 # Git repo with progressive drift (built by setup script)
│   └── benchmarks/
│       ├── test_parsing_perf.py      # Parsing stage benchmarks at various scales
│       └── test_leiden_perf.py       # Leiden detection benchmarks on synthetic graphs
└── docs/
    └── ci-integration.md             # Manual CI integration guide for v0
```

## Key Design Decisions

### KD1: Measurement-Only, No Classification

SDI reports raw measurements (pattern entropy, velocity vectors, boundary spread counts) but never classifies changes as "drift" or "migration." Teams declare migration intent via per-category threshold overrides with expiry dates in config. This was an explicit design choice over automatic drift-vs-evolution classification, which was rejected because it requires opinionated heuristics (violating the measurement-over-opinion principle) and creates dangerous false negatives in CI gates.

### KD2: YAML for Boundaries, TOML for Config

Two distinct configuration artifacts serve different audiences. TOML (`.sdi/config.toml`) handles tool configuration because it is the Python ecosystem standard, has clear semantics, and avoids YAML indentation fragility. YAML (`.sdi/boundaries.yaml`) handles boundary specifications because boundary specs are lists-of-objects with comments carrying architectural rationale — YAML's comment support and list syntax are better suited. These are two artifacts with different audiences: config is a developer settings file; boundaries is an architectural intent document.

### KD3: ruamel.yaml Over PyYAML (Pending Validation)

Leaning toward ruamel.yaml for boundary spec parsing because it preserves comments on round-trip, which matters since boundary specs carry architectural rationale in comments. PyYAML loses comments. This is an open question pending platform compatibility testing — if ruamel.yaml causes install friction, fall back to PyYAML and document that comments are not preserved on programmatic writes. **Default approach until resolved:** Use ruamel.yaml, pin a known-good version, document Windows install notes.

### KD4: Unweighted Edges by Default

Dependency graph edges are unweighted by default for Leiden community detection. Weighted edges (by import frequency / symbol count) are available via `weighted_edges = true` in config but are not the default. This is an open question requiring empirical benchmarking. **Default approach until resolved:** Ship unweighted, expose the toggle, collect data from early adopters.

### KD5: Static Leiden Gamma, No Auto-Tuning

Leiden's gamma (resolution parameter) defaults to 1.0 with manual override in config. Auto-tuning was considered but deferred because it adds complexity and reduces reproducibility. **Default approach until resolved:** Ship with gamma 1.0, let users tune manually, collect data on what values real projects use.

### KD6: No Custom Pattern Categories in v0

v0 ships built-in pattern categories only. The extensibility mechanism (tree-sitter query files? Python plugins? TOML DSL?) is deferred until real user feedback reveals what categories people want and how they prefer to define them. **Default approach:** Built-in categories are hardcoded in `sdi/patterns/categories.py`.

### KD7: No Cross-Language Dependency Detection in v0

Cross-language dependencies (e.g., TypeScript frontend calling Python backend via API contracts) are not modeled. v0 tracks only explicit in-language imports. Cross-language coupling requires understanding API contracts, OpenAPI specs, or protobuf definitions — a significant scope expansion that lands in v1 (see `.tekhton/DESIGN_v1.md` §6.2).

### KD8: JSON File Storage for Snapshots

Snapshots are stored as individual JSON files in `.sdi/snapshots/` with a retention limit (default: 100). Compact binary or SQLite storage is deferred. JSON is universally readable, composable with `jq`, and snapshot sizes (10–50KB) make storage trivial at the retention limit.

### KD9: Generated Code Handling Deferred

Generated/vendored code in non-standard locations (e.g., protobuf stubs alongside handwritten code) is not specially handled in v0. Default exclude patterns cover `vendor/`, `node_modules/`, `dist/`, `build/`. A dual-mechanism tagging system (explicit list + auto-detection) lands in v1 (see `.tekhton/DESIGN_v1.md` §4.4). **Default approach for v0:** Use exclude patterns in config to manually exclude known generated directories.

### KD10: src Layout for Package Structure

The project uses a `src/sdi/` layout (as opposed to flat `sdi/` at root) to prevent accidental imports from the working directory during development and to follow modern Python packaging best practices with `pyproject.toml`.

## Config Architecture

### Format and Loading

Configuration uses TOML format at `.sdi/config.toml`. Loading follows a strict precedence order (highest to lowest):

1. **CLI flags** (`--format json`, `--no-color`, etc.)
2. **Environment variables** (`SDI_LOG_LEVEL`, `SDI_WORKERS`, `SDI_CONFIG_PATH`, `NO_COLOR`)
3. **Project-local config** (`.sdi/config.toml` in repository root)
4. **Global user config** (`~/.config/sdi/config.toml`)
5. **Built-in defaults** (hardcoded in `src/sdi/config.py`)

All config keys are optional. Missing keys fall through to built-in defaults. Malformed TOML exits with code 2 and a descriptive error including file path and line number.

### Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `SDI_CONFIG_PATH` | Override config file location | `SDI_CONFIG_PATH=/etc/sdi/config.toml` |
| `SDI_SNAPSHOT_DIR` | Override snapshot storage directory | `SDI_SNAPSHOT_DIR=/tmp/snapshots` |
| `SDI_LOG_LEVEL` | Log verbosity | `SDI_LOG_LEVEL=DEBUG` |
| `SDI_WORKERS` | Parallel worker count for file parsing | `SDI_WORKERS=4` |
| `NO_COLOR` | Disable colored output (no-color.org standard) | `NO_COLOR=1` |

### Complete Default Configuration

```toml
[core]
# Languages to analyze. "auto" detects from file extensions.
languages = "auto"
# Files/directories to exclude (gitignore-style globs, additive to .gitignore)
exclude = [
  "**/vendor/**",
  "**/node_modules/**",
  "**/__pycache__/**",
  "**/dist/**",
  "**/build/**",
  "**/.git/**"
]
# Random seed for reproducible Leiden partitioning on cold start
random_seed = 42

[snapshots]
# Where to store snapshot files (relative to repo root)
dir = ".sdi/snapshots"
# Max snapshots to retain (oldest pruned on new capture). 0 = unlimited.
retention = 100

[boundaries]
# Path to boundary specification file
spec_file = ".sdi/boundaries.yaml"
# Leiden resolution parameter (higher = more, smaller clusters)
leiden_gamma = 1.0
# Consecutive runs a node must appear in new cluster before boundary updates
stability_threshold = 3
# Use weighted edges (import frequency) vs unweighted
weighted_edges = false

[patterns]
# Pattern categories to detect. "auto" uses built-in catalog for detected languages.
categories = "auto"
# Minimum AST subtree size to consider as a pattern instance (nodes)
min_pattern_nodes = 5
# Gitignore-style glob patterns. Matched files are excluded from the pattern catalog (Stage 4)
# only — they remain in the dependency graph, partition, and boundary spread calculations.
scope_exclude = []

[thresholds]
# Drift rate thresholds for `sdi check`. Per-dimension overrides below.
# Values are max acceptable delta per snapshot interval.
pattern_entropy_rate = 2.0
convention_drift_rate = 3.0
coupling_delta_rate = 0.15
boundary_violation_rate = 2.0

[change_coupling]
# Minimum co-change frequency (0.0-1.0) to flag cross-boundary coupling
min_frequency = 0.6
# Number of recent commits to analyze for co-change
history_depth = 500

[output]
# Default output format
format = "text"
# Color mode: "auto" (detect TTY), "always", "never"
color = "auto"
```

### Per-Category Threshold Override Structure

Teams declare migration intent by adding override sections with mandatory expiry dates:

```toml
[thresholds.overrides.error_handling]
pattern_entropy_rate = 5.0
expires = "2026-09-30"
reason = "Migrating to Result types per ADR-0047"

[thresholds.overrides.async_patterns]
convention_drift_rate = 6.0
expires = "2026-12-31"
reason = "Callback-to-async migration across services"
```

After the expiry date, the override is silently ignored and default thresholds resume.

### Boundary Specification (.sdi/boundaries.yaml)

```yaml
sdi_boundaries:
  version: "0.1.0"
  generated_from: "leiden-community-detection"
  last_ratified: "2026-04-03T22:00:00Z"
  ratified_by: "geoffgodwin"
  modules:
    - name: "billing"
      paths: ["src/billing/", "src/invoicing/"]
      layer: "domain"
    - name: "users"
      paths: ["src/users/", "src/auth/"]
      layer: "domain"
  layers:
    ordering: ["presentation", "domain", "infrastructure"]
    direction: "downward"
  allowed_cross_domain:
    - from: "billing"
      to: "users"
      via: "users.public_api"
      reason: "Billing needs user account status for invoice generation"
  aspirational_splits:
    - current_module: "billing"
      intended_boundary: ["billing_core", "invoicing"]
      target_date: "2026-Q3"
```

## Non-Negotiable Rules

1. **No network calls during analysis.** Every operation uses only the local filesystem and git history. No telemetry, no update checks, no remote lookups. A snapshot must be producible on an airgapped machine.

2. **No ML/LLM calls in the analysis pipeline.** SDI is a deterministic measurement instrument. Introducing non-deterministic inference into any stage of the pipeline is prohibited.

3. **Same commit + same config + same boundaries = same snapshot.** Determinism is enforced via fixed random seeds for cold-start Leiden partitioning (default seed: 42) and seeding from previous partition for warm starts.

4. **SDI never classifies code as "good" or "bad."** Pattern entropy, velocity vectors, and boundary spread are measurements. The tool never outputs value judgments about code quality. Threshold breaches are reported as "exceeded," not as "violations" or "problems."

5. **SDI never suppresses alerts automatically.** Elevated metrics are never silently accepted. Teams must declare migration intent via per-category threshold overrides with explicit expiry dates. After expiry, default thresholds resume without manual intervention.

6. **Threshold overrides must have expiry dates.** A `[thresholds.overrides.*]` section without an `expires` field is a configuration error (exit code 2). This forces teams to revisit stalled migrations.

7. **All file writes use atomic operations.** Snapshot files, config files, and boundary specs are written via `tempfile` in the target directory followed by `os.replace()`. A crash or SIGINT mid-write never produces a partial or corrupted file.

8. **Exit codes are a public API contract.** 0 = success, 1 = runtime error, 2 = config/environment error, 3 = analysis error, 10 = threshold exceeded (`sdi check` only). These semantics are stable across all versions, including pre-1.0.

9. **Logs go to stderr, data goes to stdout.** All log messages, progress bars, and spinners write to stderr. Stdout is reserved for requested output (summaries, JSON, CSV). This ensures `sdi show --format json | jq '.'` always works.

10. **Missing tree-sitter grammars are warnings, not errors.** If a detected language has no grammar, those files are skipped with a warning. Analysis continues with available languages. Only if ALL detected languages lack grammars does the command exit with code 3.

11. **Boundary specification is optional.** If `.sdi/boundaries.yaml` is absent, SDI operates with inferred boundaries only and skips intent divergence metrics. The tool must never require a boundary spec for basic operation.

12. **Config keys are never repurposed.** A config key that is removed in a future version is reserved forever. Old config files with removed keys produce a deprecation warning but do not error.

13. **Snapshots include a `snapshot_version` field.** Every snapshot JSON file includes its schema version. SDI must be able to read snapshots from older schema versions of the same major version for trend computation. Incompatible schema versions trigger a warning and baseline treatment (no delta), not an error.

14. **Pattern velocity is null on first snapshot.** The first snapshot is a baseline. Velocity vectors and deltas are reported as `null`, not zero. Zero means "no change"; null means "no previous data to compare against."

15. **Tree-sitter CSTs are not held in memory simultaneously.** Parse each file, extract features, discard the CST. Memory usage is proportional to the largest single file, not total codebase size.

16. **Snapshot retention is enforced on every capture.** After writing a new snapshot, if count exceeds the configured limit, the oldest snapshots are deleted immediately. No separate cleanup command.

## Implementation Milestones

<!-- Milestones are managed as individual files in .claude/milestones/.
     See MANIFEST.cfg for ordering and dependencies. -->

## Code Conventions

### Python Style

- **PEP 8 throughout.** Enforced by ruff linter in CI.
- **Functions, variables, modules:** `snake_case` — `compute_entropy`, `parse_cache`, `feature_record`
- **Classes:** `PascalCase` — `PatternFingerprint`, `BoundarySpec`, `DivergenceSummary`
- **Module-level constants:** `UPPER_SNAKE` — `DEFAULT_GAMMA`, `MAX_RETENTION`, `EXIT_THRESHOLD_EXCEEDED`
- **Type hints** on all public function signatures. No type hints on local variables unless the type is non-obvious from context.
- **Docstrings** on all public functions and classes, Google style:
  ```python
  def compute_entropy(catalog: PatternCatalog) -> dict[str, float]:
      """Compute pattern entropy per category.

      Args:
          catalog: Pattern catalog with grouped fingerprints.

      Returns:
          Dictionary mapping category name to entropy value (distinct shape count).
      """
  ```

### File Organization

- One module per concern, NOT one class per file. Group related classes and functions in the same module.
- New source files go under the appropriate package: `src/sdi/parsing/`, `src/sdi/graph/`, etc.
- New test files mirror source structure: `tests/unit/test_<module_name>.py`
- Maximum file length guideline: 500 lines. If a module exceeds this, consider splitting by sub-concern.

### Import Ordering

Use ruff's isort-compatible ordering:
1. Standard library imports
2. Third-party imports (tree-sitter, igraph, leidenalg, click, rich)
3. Local imports (`from sdi.config import ...`, `from sdi.parsing import ...`)

Blank line between each group.

### Error Handling

- Use specific exception types, not bare `except:`.
- Configuration errors: raise `SystemExit(2)` with descriptive message.
- Analysis errors: raise `SystemExit(3)` with descriptive message.
- Use Click's `click.echo()` for stdout and `click.echo(..., err=True)` for stderr, or Rich console equivalents.
- Top-level exception handler in `cli/__init__.py` catches unexpected exceptions, prints a user-friendly message, and exits with code 1. Full traceback only in DEBUG mode.

### Git Workflow

- **Branch naming:** `feature/<short-description>`, `fix/<short-description>`, `milestone-<N>/<short-description>`
- **Commit messages:** imperative mood, first line under 72 characters. Example: `Add Python language adapter for tree-sitter parsing`
- **PR process:** one PR per milestone or per logical unit of work. PR description must include acceptance criteria verification.

### State Management

SDI has no persistent runtime state. Each invocation reads config, reads cached data if available, computes, writes output, and exits. State is in files (config, snapshots, cache), not in memory across invocations.

## Critical System Rules

1. **Atomic file writes are mandatory for all `.sdi/` file operations.** Use `tempfile.NamedTemporaryFile(dir=target_dir, delete=False)` followed by `os.replace(tmpfile, target)`. Never write directly to the target path. A partial snapshot file is a data corruption bug.

2. **Tree-sitter CSTs must be discarded after feature extraction.** The pipeline must parse a file, extract its `FeatureRecord`, and release the CST before parsing the next file (in each worker). Holding all CSTs simultaneously is a memory safety violation.

3. **Leiden community detection must be seeded.** On cold start, use `config.random_seed` (default: 42). On warm start, seed from `.sdi/cache/partition.json`. Never run unseeded Leiden — non-deterministic results violate the reproducibility guarantee.

4. **Snapshot `snapshot_version` field is mandatory.** A snapshot without this field is invalid and must not be written. Delta computation against a snapshot with an incompatible version must warn and treat it as a baseline (no delta), never crash.

5. **Per-category threshold overrides without `expires` are rejected.** Config validation must fail (exit code 2) if any `[thresholds.overrides.*]` section is missing the `expires` key. This enforces the principle that alert suppression is always time-boxed.

6. **Exit code 10 is exclusively for threshold breach in `sdi check`.** No other command may exit with code 10. Other commands use 0 (success), 1 (runtime error), 2 (config/env error), or 3 (analysis error).

7. **First snapshot has null deltas.** The delta computation function must return null (not zero) for all dimensions when there is no previous snapshot. Zero means "no change between two snapshots"; null means "no previous data exists."

8. **Pattern velocity and boundary spread are never used for classification.** These are raw measurements included in snapshot output. SDI code must never use them to make decisions about whether a change is "drift" or "migration" or to suppress alerts.

9. **No command modifies the working tree.** `sdi snapshot --commit REF` must access files at the specified commit without running `git checkout`. Use `git show REF:path` or `git archive` to read historical file contents.

10. **Snapshot retention enforcement happens synchronously after write.** After `sdi snapshot` writes a new snapshot file, it must check the snapshot count and delete the oldest excess files before returning. Deferred cleanup is not acceptable — the retention limit must be a hard guarantee.

11. **Progress output goes to stderr, data goes to stdout.** Rich progress bars, spinners, and log messages must all write to `stderr`. This rule has no exceptions — a Rich component writing to stdout corrupts piped JSON/CSV output.

12. **Missing boundary spec is normal operation, not a degraded mode.** When `.sdi/boundaries.yaml` is absent, SDI must compute all metrics except intent divergence. The output must not include warnings about missing boundaries — absence of a ratified spec is an expected state for new projects.

## What Not to Build Yet

**IDE/Editor Plugin** — Requires stable API and snapshot schema. Evaluate after v1.0 when the schema is frozen.

**SaaS Dashboard / Web UI** — SDI is a measurement instrument, not a platform. Output is JSON consumable by existing dashboards (Grafana, Datadog). A hosted UI is a separate product.

**Auto-Remediation / Gardener Agent** — SDI detects and measures drift; it never fixes it. A companion tool generating consolidation PRs is a separate project.

**GitHub Actions Marketplace Action** — Document manual CI integration in v0 (`pip install sdi && sdi check`). A polished reusable action with PR comments and badges lands in v1 (see `.tekhton/DESIGN_v1.md` §7.2).

**Plugin System for Custom Analyzers** — V1 ships built-in pattern categories only. Design extensibility after real user feedback on what categories people need.

**Cross-Language Dependency Inference** — Detecting implicit dependencies between services (TypeScript calling Python via API) requires API contract parsing (OpenAPI, protobuf). V1 tracks only explicit in-language imports.

**Historical Backfill UX** — `sdi snapshot --commit REF` works for individual commits. Batch backfill across hundreds of commits (parallelism, progress, storage) is not designed. Users can script it with a bash loop.

**Standalone Binary Distribution** — PyInstaller/Nuitka packaging deferred until the dependency tree stabilizes. Tree-sitter grammar loading from bundled binaries has known complexity.

**Real-Time / Watch Mode** — No file watcher daemon. CLI invocation on merge events is the intended cadence. Watch mode violates the Unix philosophy constraint.

**Automatic Drift-vs-Evolution Classification** — Explicitly rejected (see Design Decision KD1). SDI reports raw measurements; humans declare migration intent via threshold overrides. If future versions add classification, it would be opt-in advisory only, never gate suppression.

**Stdin Input** — `sdi diff` does not read snapshot JSON from stdin in v0. Stdin support lands in v1 (see `.tekhton/DESIGN_v1.md` §7.3).

**`sdi config` Subcommand** — No config management command. Edit `.sdi/config.toml` directly.

## Testing Strategy

### Framework and Tools

- **pytest** for all tests
- **pytest-cov** for coverage reporting (target: 80%+ unit test coverage)
- **pytest-benchmark** for performance benchmarks (not in normal CI, triggered on release tags)
- **ruff** for linting (PEP 8, import sorting)
- **mypy** for type checking (`disallow_untyped_defs = true` for `sdi/` package)

### Test Categories

**Unit tests (`tests/unit/`):** Test individual functions and classes in isolation. Mock external dependencies (filesystem, git, tree-sitter) where needed. Cover all config loading paths, all delta computations, all fingerprint operations, all boundary spec parsing edge cases.

**Integration tests (`tests/integration/`):** Test the full pipeline end-to-end against fixture repos. Run actual CLI commands as subprocesses. Verify stdout/stderr output, exit codes, and created files. No mocks — these test real tree-sitter parsing, real igraph operations, and real filesystem interactions.

**Benchmark tests (`tests/benchmarks/`):** Performance regression tests on synthetic data at various scales. Not run in normal CI — triggered manually or on release tags. Use pytest-benchmark for consistent measurement.

### Test Commands

```bash
# Run all unit tests with coverage
pytest tests/unit/ --cov=sdi --cov-report=term-missing

# Run integration tests
pytest tests/integration/

# Run all tests
pytest

# Run benchmarks (manual only)
pytest tests/benchmarks/ --benchmark-only

# Lint
ruff check src/ tests/

# Type check
mypy src/sdi/

# Format check
ruff format --check src/ tests/
```

### Fixture Repos

| Fixture | Purpose | Structure |
|---|---|---|
| `tests/fixtures/simple-python/` | Baseline for most tests. Small Python project with known imports, one pattern variant, one boundary crossing. | 5–10 Python files with explicit dependency structure |
| `tests/fixtures/multi-language/` | Cross-language tests. Python + TypeScript files. | 3–5 files per language |
| `tests/fixtures/high-entropy/` | Pattern fingerprinting accuracy. 4+ error handling styles, 3+ data access patterns. | 10+ Python files with deliberate pattern variety |
| `tests/fixtures/evolving/` | Trend and diff testing. Git repo with 5+ commits introducing progressive drift. | Built by `setup_fixture.py` script |

### Testing Patterns

- **Fixture repos over mocks** for integration tests. Real tree-sitter parsing, real igraph graphs.
- **Mock filesystem and git** for unit tests where the behavior under test is computation, not I/O.
- **Deterministic test data.** No random test inputs. All fixtures have known, documented expected outputs.
- **No network access in tests.** All tests run offline.
- **No timezone dependence.** Use UTC everywhere, including in fixture timestamps.
- **Normalize dynamic output in snapshot tests.** Replace timestamps, paths, and hashes with placeholders before comparison.

## Development Environment

### Prerequisites

- **Python 3.10+** (3.11+ recommended for `tomllib` stdlib support)
- **git** in PATH (SDI shells out to git for history analysis)
- No other system dependencies — all Python packages distribute pre-built wheels

### Setup

```bash
# Clone
git clone https://github.com/GeoffGodwin/sdi.git
cd sdi

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install all language grammars
pip install -e ".[all]"

# Install pre-push hooks (runs ruff check + ruff format --check)
pre-commit install --hook-type pre-push

# Verify installation
sdi --version
```

### Build

```bash
# Build wheel and sdist
python -m build

# Verify package metadata
twine check dist/*
```

### Test

```bash
# Unit tests with coverage
pytest tests/unit/ --cov=sdi --cov-report=term-missing

# Integration tests
pytest tests/integration/

# All tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/sdi/

# Format check
ruff format --check src/ tests/
```

### Environment Variables for Development

| Variable | Purpose | Example |
|---|---|---|
| `SDI_LOG_LEVEL` | Set log verbosity for debugging | `SDI_LOG_LEVEL=DEBUG` |
| `SDI_WORKERS` | Force worker count (1 for debugging) | `SDI_WORKERS=1` |
| `SDI_CONFIG_PATH` | Override config location for testing | `SDI_CONFIG_PATH=/tmp/test-config.toml` |
| `NO_COLOR` | Disable colored output | `NO_COLOR=1` |

### Quick Smoke Test

After setup, verify the tool works end-to-end:

```bash
cd tests/fixtures/simple-python/
sdi init
sdi snapshot
sdi show
sdi catalog
```
<!-- tekhton-managed -->
