# Design Document — Structural Divergence Indexer (SDI)

## Developer Philosophy & Constraints

SDI is built on a set of non-negotiable architectural principles that govern every design decision, contribution, and release. These constraints are not aspirational — they are enforced in code review, CI gates, and the tool's own architecture.

### Measurement Over Opinion

Every claim SDI makes about a codebase must be backed by a concrete, reproducible measurement derived from AST analysis or dependency graph structure. No heuristics that cannot be explained. No scores without traceable inputs. If a metric cannot be decomposed into its constituent measurements, it does not ship.

### Fever Chart, Not Thermometer

Every metric SDI produces must be trackable over time. Point-in-time values are necessary but insufficient. The primary output is always the trend: the rate of change of structural coherence, not the absolute state. Alerts fire on rate-of-change thresholds, not absolute values. A codebase with high pattern entropy that has been stable for six months is not alarming; a codebase with low entropy that doubled this week is.

### Automated Inference, Human Ratification

SDI never tells a team what their architecture "should" be. It infers structural boundaries from the code via community detection (Leiden algorithm), proposes them, and waits for a human to ratify, merge, split, or override. The tool measures divergence from declared intent, not from its own opinions. This principle extends to pattern categories: SDI detects structural shapes and counts them, but never classifies code as "good" or "bad."

### Safe Defaults, Zero Mandatory Config

Running `sdi snapshot` on an un-initialized repository produces useful output using purely inferred boundaries and auto-detected language patterns. Configuration refines and ratifies — it is never required for first use. A developer should be able to clone a repo, install SDI, and get a meaningful structural fingerprint in under a minute with zero setup.

### Composable Unix Tooling

SDI reads from the filesystem and git history, writes JSON snapshots and human-readable reports to stdout/files, and exits with meaningful codes. It composes with `jq`, `diff`, CI pipelines, and git hooks. No daemon mode, no server, no interactive TUI in v1. Every output format is designed for downstream consumption by standard Unix tools.

### Language-Agnostic Core, Language-Specific Adapters

The dependency graph, community detection, pattern fingerprinting, and snapshot diffing are language-agnostic. Language specifics (import resolution, AST queries for pattern categories) live in adapter modules that can be added independently. Tree-sitter provides the parsing primitive, ensuring consistent AST representation across all supported languages.

### Deterministic and Reproducible

Given the same commit, the same configuration, and the same boundary specification, SDI produces the same snapshot. The Leiden algorithm is seeded from the previous partition for stability, but cold-start runs use a fixed random seed so that results are reproducible across machines and CI environments.

### Fast Enough for CI

A snapshot capture must complete in seconds to low minutes on codebases up to 500K lines. This is a hard constraint — SDI runs on every merge to the primary branch. Tree-sitter parsing is already fast; the budget concern is graph analysis on large dependency graphs. Performance targets are codified in benchmarks and tracked across releases.

### Drift vs. Evolution Is Measured, Not Classified

SDI computes the second-order signals that distinguish incoherent structural drift from intentional architectural migration — pattern velocity vectors (instance count deltas per shape across snapshots) and boundary-locality (how many boundaries a pattern variant spans). These are objective measurements reported in the snapshot. SDI never classifies a change as "drift" or "migration" — that is a human judgment. Teams declare migration intent through per-category threshold overrides with expiry dates, mirroring the boundary ratification model: automated inference surfaces the data, human declaration captures the intent.

### Banned Anti-Patterns

| Anti-Pattern | Rationale |
|---|---|
| ML/LLM calls in the analysis pipeline | SDI is a measurement instrument, not an AI tool. Determinism and reproducibility are non-negotiable. |
| Network calls during analysis | Everything operates on local filesystem and git history. No telemetry, no update checks, no remote lookups during analysis. |
| Opinions about code quality | SDI measures structural divergence, not whether code is "good" or "bad." A high pattern entropy might be perfectly acceptable for a given project stage. |
| Automatic alert suppression | SDI never decides that elevated metrics are acceptable. Teams declare intent via per-category threshold overrides with expiry dates. The tool enforces declared thresholds; it does not infer which changes are "okay." |

## Project Overview

SDI (Structural Divergence Indexer) is a CLI tool that computes and tracks the Structural Divergence Index — a composite metric measuring the rate of structural drift in a codebase across four dimensions: pattern entropy, convention drift rate, coupling topology delta, and boundary violation velocity. The metric is the Structural Divergence Index; the tool is the Structural Divergence Indexer.

### The Problem

Current quality tooling — linters, static analyzers, code review — evaluates individual changes in isolation. Each change may be perfectly correct on its own, yet the collective direction of all changes may be incoherent. This gap is especially pronounced in codebases where multiple independent contributors (human or AI agent) generate code concurrently without shared structural awareness. The Structural Divergence Index fills the gap between "every individual change is good" and "the collective direction of all changes is coherent."

### The Analogy

SDI is the urban planner's aerial photograph overlaid on the master plan, complementing the building inspector (linter) and structural engineer (static analyzer) that already exist. It captures periodic structural fingerprints (snapshots) and diffs them over time to produce trend data and actionable alerts.

### Target Users

Software engineers, tech leads, and engineering managers responsible for the structural health of codebases. The primary use case is teams using AI-assisted development at scale, where multiple independent contributors are generating code concurrently without shared structural awareness — but the tool is equally valuable for any team experiencing rapid growth or distributed development.

### Distribution Model

Open source under MIT or Apache 2.0 license. The tool and its output format are public goods. The value proposition is the measurement methodology, not proprietary analysis.

### Invocation Frequency

Typically once per merge to the primary integration branch. High-velocity teams might run it 10–50 times per day. CI integration is the primary use case, with manual invocation for exploration and debugging.

## Tech Stack

### Language: Python 3.10+

Python was selected for the following reasons:

- **tree-sitter** has mature Python bindings (v0.24+) for multi-language AST parsing
- The **Leiden algorithm** has a maintained Python package (`leidenalg` by V.A. Traag)
- **igraph** has a mature Python interface for graph analysis
- Python is the lingua franca for developer tooling that interacts with AST parsing
- Performance-critical paths (tree-sitter parsing, igraph graph operations) are backed by C/C++ libraries, so Python overhead is negligible for the orchestration layer

### Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `tree-sitter` | >=0.24 | Multi-language AST parsing |
| `tree-sitter-python`, `-javascript`, `-typescript`, `-go`, `-java`, `-rust` | latest | Per-language grammar packages |
| `leidenalg` | latest | Leiden community detection algorithm |
| `igraph` | latest | Graph construction, analysis, cycle detection, centrality metrics |
| `click` | latest | CLI framework (argument parsing, subcommands, help generation) |
| `rich` | latest | Terminal output formatting (tables, progress bars, colored diff output) |
| `tomli` / `tomllib` | latest | TOML config parsing (`tomllib` is stdlib in 3.11+, `tomli` for 3.10) |
| `tomli-w` | latest | TOML writing for `sdi init` config generation |
| `ruamel.yaml` or `PyYAML` | latest | YAML parsing for boundary specification files (see Open Design Questions) |
| `pytest` | latest | Testing framework |
| `pytest-cov` | latest | Coverage reporting |

### Serialization

- **JSON** for snapshot files (stdlib `json` module) — machine-readable, universally supported
- **TOML** for configuration files — human-readable with clear spec, consistent with Python ecosystem (`pyproject.toml`)
- **YAML** for boundary specification files — better expressiveness for lists-of-objects with comments that carry architectural rationale

### Build & Distribution

- **Build backend**: `hatchling` or `setuptools` with `pyproject.toml` (PEP 621)
- **Primary distribution**: PyPI (`pip install sdi`)
- **Secondary distribution**: Homebrew formula in a `homebrew-sdi` tap repository
- **Stretch goal**: Standalone binaries via PyInstaller or Nuitka on GitHub Releases (not v1)

## Command Taxonomy

SDI is a multi-command CLI in the git style. The root command is `sdi`. All subcommands are single words — no multi-word commands.

### sdi init

Initializes SDI configuration in the current repository. Creates the `.sdi/` directory with default config, runs initial structural inference to propose boundaries, and optionally writes a starter boundary specification for ratification.

**Syntax:**
```
sdi init [--force] [--language LANG]...
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--force` | boolean | false | Overwrite existing `.sdi/` configuration |
| `--language` | string (repeatable) | auto-detect | Explicitly specify languages to analyze |

**Examples:**
```bash
sdi init
sdi init --language python --language typescript
```

### sdi snapshot

Captures the current structural fingerprint of the codebase. Parses source via tree-sitter, builds the dependency graph, runs Leiden community detection (seeded from previous partition if available), computes all four SDI dimensions, and writes a snapshot file.

**Syntax:**
```
sdi snapshot [--output PATH] [--commit REF] [--format json|summary]
```

**Flags:**

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--output` | `-o` | path | `.sdi/snapshots/<timestamp>-<short-sha>.json` | Write snapshot to specific path |
| `--commit` | | git ref | working tree | Analyze a specific git commit instead of working tree |
| `--format` | `-f` | `json\|summary` | json + summary | `json` writes full snapshot file; `summary` prints human-readable summary to stdout. Default behavior writes JSON file and prints summary to terminal. |

**Examples:**
```bash
sdi snapshot
sdi snapshot --commit HEAD~5
sdi snapshot --output /tmp/baseline.json --format json
```

### sdi diff

Compares two snapshots and shows what changed structurally. If no arguments are provided, compares the two most recent snapshots. If one argument is provided, compares it against the most recent.

**Syntax:**
```
sdi diff [SNAPSHOT_A] [SNAPSHOT_B] [--format json|text]
```

**Flags:**

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--format` | `-f` | `text\|json` | `text` | `text` for human-readable colored diff; `json` for machine-readable delta object |

**Examples:**
```bash
sdi diff
sdi diff .sdi/snapshots/20260401-a1b2c3d.json .sdi/snapshots/20260403-d4e5f6a.json
sdi diff --format json
```

### sdi trend

Shows trend data across multiple snapshots — the fever chart. Displays the trajectory of each SDI dimension over time.

**Syntax:**
```
sdi trend [--last N] [--dimension DIMENSION] [--format text|json|csv]
```

**Flags:**

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--last` | `-n` | integer | 20 | Number of most recent snapshots to include |
| `--dimension` | | string | all | Filter to a specific dimension: `pattern_entropy`, `convention_drift`, `coupling_topology`, `boundary_violations` |
| `--format` | `-f` | `text\|json\|csv` | `text` | `text` for terminal table/sparklines; `json` for structured data; `csv` for spreadsheet import |

**Examples:**
```bash
sdi trend
sdi trend --last 50 --dimension pattern_entropy
sdi trend --format csv > metrics.csv
```

### sdi check

CI-friendly gate command. Captures a snapshot (or uses a provided one), computes drift rates against recent history, and exits non-zero if any rate exceeds the configured threshold. Designed for use in CI pipelines and git hooks.

**Syntax:**
```
sdi check [--threshold FLOAT] [--dimension DIMENSION] [--snapshot PATH]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--threshold` | float | from config | Override drift rate threshold |
| `--dimension` | string | all | Check only a specific dimension |
| `--snapshot` | path | capture new | Use an existing snapshot instead of capturing a new one |

**Exit Codes:**

| Code | Meaning |
|---|---|
| 0 | All dimensions within threshold |
| 1 | Unexpected runtime error |
| 2 | Configuration or environment error |
| 3 | Analysis error (e.g., no supported languages found) |
| 10 | One or more dimensions exceeded threshold (prints which ones) |

**Examples:**
```bash
sdi check
sdi check --threshold 0.5 --dimension boundary_violations
sdi check --snapshot .sdi/snapshots/latest.json
```

### sdi show

Human-readable summary of the current state. Shows the most recent snapshot data, current boundary map, pattern catalog summary, and any active alerts. This is the "what does my codebase look like right now" command.

**Syntax:**
```
sdi show [--format text|json] [--verbose]
```

**Flags:**

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--format` | `-f` | `text\|json` | `text` | Output format |
| `--verbose` | `-v` | boolean | false | Include full pattern catalog and boundary details |

**Examples:**
```bash
sdi show
sdi show --verbose
sdi show --format json | jq '.pattern_catalog'
```

### sdi boundaries

Views, proposes, or manages architectural boundary definitions. Without flags, shows the current ratified boundary map. With `--propose`, runs Leiden inference and shows proposed changes. With `--ratify`, opens the boundary spec in `$EDITOR` for interactive editing.

**Syntax:**
```
sdi boundaries [--propose] [--ratify] [--export PATH] [--format text|yaml]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--propose` | boolean | false | Run structural inference and show proposed boundary map (does not modify ratified spec) |
| `--ratify` | boolean | false | Open boundary spec in `$EDITOR` for ratification after reviewing proposal |
| `--export` | path | — | Export current boundary map to a file |
| `--format` | `text\|yaml` | `text` | Output format for display |

**Examples:**
```bash
sdi boundaries
sdi boundaries --propose
sdi boundaries --propose --ratify
```

### sdi catalog

Views the detected pattern catalog — all structural fingerprints grouped by operation category. Shows which patterns exist, how many variants of each, and which is marked canonical.

**Syntax:**
```
sdi catalog [--category CATEGORY] [--format text|json]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--category` | string | all | Filter to a specific pattern category |
| `--format` | `text\|json` | `text` | Output format |

**Examples:**
```bash
sdi catalog
sdi catalog --category error_handling --format json
```

## Input Sources & Formats

SDI reads from five distinct input sources, each with specific formats, discovery rules, and failure modes.

### Source Code Files (via tree-sitter)

SDI accepts any language with a tree-sitter grammar. V1 targets six languages: Python, TypeScript, JavaScript, Go, Java, and Rust. Additional languages are added by installing the corresponding tree-sitter grammar package.

File discovery walks the repository tree, filtering by `.gitignore` and configured exclude patterns. Language detection uses file extension as the primary method with tree-sitter grammar probing as a fallback. Files that match no known grammar are silently skipped.

### Git History (via subprocess)

SDI shells out to `git` for change coupling analysis (co-change frequency), commit-to-snapshot association, and convention drift rate computation (when were new patterns introduced). It reads `git log`, `git diff`, and `git show`. A git repository is required — SDI exits with code 2 if not in a git repo.

### Configuration File (.sdi/config.toml)

TOML format. Discovery order with highest precedence first:

1. CLI flags
2. Environment variables (`SDI_*` prefix)
3. `.sdi/config.toml` in repository root
4. `~/.config/sdi/config.toml` (global user defaults)
5. Built-in defaults

Malformed config exits with code 2 and a specific parse error message including the file path and line number.

### Boundary Specification (.sdi/boundaries.yaml)

YAML format. This is the human-ratified architectural intent artifact, read on every snapshot capture for intent divergence detection. It is optional — if absent, SDI operates with inferred boundaries only and skips intent divergence metrics.

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
    - name: "api"
      paths: ["src/api/", "src/routes/"]
      layer: "presentation"
    - name: "persistence"
      paths: ["src/data/", "src/repositories/"]
      layer: "infrastructure"
  layers:
    ordering: ["presentation", "domain", "infrastructure"]
    direction: "downward"  # presentation -> domain -> infrastructure
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

Key concepts in the boundary specification:

- **modules**: Ratified boundary definitions with file path patterns and layer assignment
- **layers**: Optional layered architecture constraint with allowed dependency direction
- **allowed_cross_domain**: Explicitly permitted cross-boundary dependencies with rationale
- **aspirational_splits**: Planned future boundaries that don't exist in code yet but should be tracked for progress toward separation

### Previous Snapshots (.sdi/snapshots/*.json)

JSON format, versioned via a `snapshot_version` field in every snapshot file. Read for seeding the Leiden partition, computing deltas and trends, and drift rate calculation. If no previous snapshots exist, the first snapshot is a baseline with no delta information.

### Stdin

SDI does not read from stdin in v1. All input is file-based. Piping snapshot JSON into `sdi diff` is a future consideration but out of initial scope.

### Environment Variables

| Variable | Purpose |
|---|---|
| `SDI_CONFIG_PATH` | Override config file location |
| `SDI_SNAPSHOT_DIR` | Override snapshot storage directory |
| `SDI_LOG_LEVEL` | Set log verbosity (`DEBUG`, `INFO`, `WARN`, `ERROR`) |
| `SDI_WORKERS` | Override parallel worker count for file parsing |
| `NO_COLOR` | Disable colored output (industry standard convention) |

### Precedence Order

CLI flags > environment variables > project-local config (`.sdi/config.toml`) > global user config (`~/.config/sdi/config.toml`) > built-in defaults.

### Malformed Input Behavior

Malformed configuration or boundary specs cause an immediate exit with code 2 and a descriptive error message including the file path, line number, and the nature of the parse error. Missing tree-sitter grammars for detected languages produce a warning but do not block analysis — those files are excluded and the snapshot proceeds with available languages.

## Output Formatting & Modes

### Stdout Output

SDI supports three output modes, controlled by the `--format` flag:

**Human mode** (default when stdout is a TTY): Colored, formatted tables via the Rich library. Snapshot summaries, diff views with red/green deltas, trend sparklines, and boundary maps with indented tree display. Uses Unicode box-drawing characters for structure.

**Machine mode** (`--format json`): Structured JSON objects. One JSON document per invocation, no streaming. Designed for piping to `jq` or consumption by CI scripts.

**CSV mode** (`--format csv`, `sdi trend` only): Headerless CSV for spreadsheet import.

### Stderr Output

All log messages (`INFO`, `WARN`, `ERROR`, `DEBUG`) go to stderr. Progress indicators (tree-sitter parsing progress, graph analysis spinners) go to stderr. This ensures stdout is always clean for piping, even in human mode.

### Files Created

| File | Created By | Purpose |
|---|---|---|
| `.sdi/config.toml` | `sdi init` | Project configuration |
| `.sdi/boundaries.yaml` | `sdi init`, `sdi boundaries --ratify` | Ratified boundary specification |
| `.sdi/snapshots/<timestamp>-<short-sha>.json` | `sdi snapshot` | Structural fingerprint snapshot |
| `.sdi/cache/` | `sdi snapshot` (internal) | Parse cache, partition cache, fingerprint cache |

### Exit Codes

Exit codes are consistent across all commands:

| Code | Meaning | Commands |
|---|---|---|
| 0 | Success (for `sdi check`: all dimensions within threshold) | All |
| 1 | General runtime error or unexpected failure | All |
| 2 | Configuration or environment error (missing config, invalid TOML, no git repo) | All |
| 3 | Analysis error (tree-sitter grammar not available, graph construction failed) | All |
| 10 | One or more dimensions exceeded threshold | `sdi check` only |

### Output Control Flags

Available on all commands:

| Flag | Values | Description |
|---|---|---|
| `--format` | `text\|json\|csv` | Output format (CSV only where applicable) |
| `--no-color` | boolean | Disable colored output (also respects `NO_COLOR` env var) |
| `--quiet` / `-q` | boolean | Suppress non-essential output (only errors and requested data) |
| `--verbose` / `-v` | boolean | Include additional detail (full pattern lists, all boundary details) |

### TTY Detection

When stdout is not a TTY, SDI automatically switches to uncolored output and suppresses progress indicators. The `--format` flag still defaults to `text` (not `json`) to avoid surprising users who redirect to a file expecting readable text.

## Configuration System

### Format and Rationale

Configuration uses TOML (`.sdi/config.toml`). TOML is human-readable, has a clear specification, supports nested tables without YAML's indentation fragility, and is the standard for Python project configuration (`pyproject.toml`). The boundary specification uses YAML as a separate artifact because boundary specs contain lists-of-objects with comments that carry architectural rationale — these are two distinct artifacts with different audiences.

### Config File Locations

- **Project-local**: `.sdi/config.toml` (in repository root, committed to VCS)
- **Global defaults**: `~/.config/sdi/config.toml` (user-level preferences)

### Discovery Order

Highest precedence first:

1. CLI flags (`--format json`, `--no-color`, etc.)
2. Environment variables (`SDI_LOG_LEVEL`, `SDI_WORKERS`, `SDI_CONFIG_PATH`, `NO_COLOR`)
3. Project-local config (`.sdi/config.toml` in repo root)
4. Global user config (`~/.config/sdi/config.toml`)
5. Built-in defaults (hardcoded in `sdi/config.py`)

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

[thresholds]
# Drift rate thresholds for `sdi check`. Per-dimension overrides below.
# Values are max acceptable delta per snapshot interval.
pattern_entropy_rate = 2.0
convention_drift_rate = 3.0
coupling_delta_rate = 0.15
boundary_violation_rate = 2.0

# Per-category threshold overrides for planned migrations.
# Teams declare elevated thresholds with an expiry date when they expect
# a category to show increased drift during an intentional migration.
# After the expiry date, the override is ignored and defaults resume.
#
# [thresholds.overrides.error_handling]
# pattern_entropy_rate = 5.0
# expires = "2026-09-30"
# reason = "Migrating to Result types per ADR-0047"
#
# [thresholds.overrides.async_patterns]
# convention_drift_rate = 6.0
# expires = "2026-12-31"
# reason = "Callback-to-async migration across services"

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

### Configuration Management

There is no `sdi config` subcommand in v1. Configuration is edited directly in the TOML file. `sdi init` generates the file with commented defaults. Config changes take effect on the next command invocation — no restart or daemon involved.

To reset to defaults: delete `.sdi/config.toml` and run `sdi init` to regenerate, or manually remove specific keys so they fall through to built-in defaults.

## Core Processing Logic

The core pipeline has five stages, executed sequentially on every `sdi snapshot` invocation. Each stage has defined inputs, outputs, complexity characteristics, and failure modes.

### Stage 1: Source Parsing (tree-sitter)

The parser walks the repository file tree, filtering by `.gitignore` and configured exclude patterns. For each source file:

1. Detect language by file extension, with tree-sitter grammar probe as fallback
2. Parse the file into a concrete syntax tree (CST) via tree-sitter
3. Extract structural features: imports/dependencies, function/class definitions, exported symbols, and pattern-relevant AST subtrees (try/catch blocks, API call patterns, data access patterns, etc.)
4. Emit a per-file feature record (symbols, imports, pattern instances)

**Complexity**: O(N) in total lines of code. Tree-sitter native parsing runs at approximately 1M lines/sec; the bottleneck is file I/O.

**Parallelization**: This stage is embarrassingly parallel — each file is independent. SDI uses `concurrent.futures.ProcessPoolExecutor` with worker count defaulting to `os.cpu_count()`, configurable via `SDI_WORKERS`.

**Failure mode**: Missing grammar for a detected language. This is a graceful skip with a warning — that language's files are excluded from analysis but do not block the snapshot. If all detected languages lack grammars, the command exits with code 3.

### Stage 2: Dependency Graph Construction

Builds a directed graph where nodes are files (or modules, configurable) and edges are import/dependency relationships extracted in Stage 1. Cross-language dependency semantics are normalized into a language-agnostic graph: Python imports, JS/TS imports/requires, Go imports, Java imports, and Rust `use` statements all produce the same edge type.

Edges are optionally weighted by import frequency (number of symbols imported), controlled by the `weighted_edges` config key. Graph metrics are computed: node count, edge count, density, connected components.

**Output**: igraph `Graph` object + metrics dictionary.

**Complexity**: O(N + E) where N = files, E = import relationships.

**Failure mode**: Cyclic import resolution ambiguity. Handled by recording all edges including cycles — cycles are a measurement target, not an error.

### Stage 3: Community Detection (Leiden Algorithm)

If a previous partition exists (`.sdi/cache/partition.json`), seeds from it for stability. On cold start, uses the configured `random_seed` for reproducibility. Runs the Leiden algorithm via `leidenalg` with the configured gamma (resolution parameter).

Post-detection processing:

- Compute partition stability score versus previous run (percentage of nodes that kept membership)
- Apply stability threshold: only update boundary map if a node moved in N consecutive runs (debounce, controlled by `stability_threshold`)
- Compute dependency directionality between clusters, interface surface area ratio per cluster, and change coupling from git history

**Output**: Cluster assignments, stability score, inter-cluster dependency graph, surface area ratios, change coupling flags.

**Complexity**: Leiden is O(E) per iteration, typically converging in 2–5 iterations. The igraph C implementation keeps this fast even for large graphs.

**Failure mode**: Graph too small for meaningful clustering (fewer than 10 nodes). Reports "insufficient structure for boundary detection" and skips boundary metrics without error.

### Stage 4: Pattern Fingerprinting

For each built-in pattern category, queries the AST features from Stage 1 using category-specific tree-sitter queries, then computes structural fingerprints.

**Built-in pattern categories (v1):**

| Category | What It Detects |
|---|---|
| `error_handling` | try/catch/except blocks, error propagation patterns, Result/Either types |
| `data_access` | Database queries, ORM calls, repository pattern implementations, raw SQL vs query builder vs ORM |
| `api_validation` | Input validation at API boundaries, schema validation, type checking guards, assertion patterns |
| `logging` | Log call patterns, structured vs unstructured logging, log level usage |
| `dependency_injection` | Constructor injection, factory patterns, service locators, global state access |
| `async_patterns` | async/await usage, callback styles, promise chains, concurrency primitives |
| `config_access` | How configuration values are read (env vars, config objects, hardcoded values, magic strings) |

For each pattern instance, SDI computes a structural fingerprint: a normalized representation of the AST subtree shape (node types and structure, stripped of identifiers and literals). Fingerprints are grouped by category and hashed for O(1) grouping. The most frequent shape per category is marked as canonical (or user-declared in config).

**Derived measurements:**

- **Pattern entropy**: Count of distinct structural shapes per category
- **Per-shape velocity**: Instance count delta versus previous snapshot (positive = growing, negative = shrinking, zero = stable). This is a pure integer delta, not a classification.
- **Per-shape boundary spread**: Count of distinct boundaries each shape spans, cross-referenced against the partition from Stage 3. This is a pure count, not a judgment.

**Complexity**: O(P) where P = total pattern instances across all categories. Velocity and boundary spread add O(S × B) where S = shapes and B = boundaries, which is negligible.

**Failure mode**: No pattern instances found for a category. Reports zero entropy, not an error. No previous snapshot for velocity: reports velocity as null (baseline snapshot).

### Stage 5: Snapshot Assembly & Delta Computation

Combines outputs from Stages 2–4 into a snapshot JSON document. If a previous snapshot exists, computes deltas for all four SDI dimensions:

| Dimension | What It Measures |
|---|---|
| Pattern entropy delta | Change in distinct shapes per category |
| Convention drift rate | Net new patterns minus consolidated patterns since last snapshot |
| Coupling topology delta | Structural comparison of dependency graphs (cycle count change, hub concentration change, max depth change) |
| Boundary violation velocity | New cross-boundary dependencies since last snapshot, compared against ratified boundary spec if available |

If a boundary specification exists, computes intent divergence (detected boundaries versus ratified spec). Writes the snapshot to the configured directory and prints a human-readable summary to stdout.

**Complexity**: O(N + E) for graph comparison, O(C) for pattern catalog diff where C = categories.

**Failure mode**: Previous snapshot has incompatible schema version. Warns and treats as baseline (no delta computed).

## Error Handling & Diagnostics

### Error Reporting Strategy

All errors go to stderr. Format: `[LEVEL] message` where LEVEL is `ERROR`, `WARN`, or `DEBUG`. Colors are applied when stderr is a TTY (red for `ERROR`, yellow for `WARN`, dim for `DEBUG`). The Rich library handles all formatting.

### Error Categories

**Configuration errors (exit code 2):**
- Missing or malformed `.sdi/config.toml`: `Error: invalid config at .sdi/config.toml line 14: expected string value for 'core.languages'`
- Invalid boundary spec YAML: parse error with line number
- Suggestion provided: `Run 'sdi init' to generate a default configuration`

**Environment errors (exit code 2):**
- Not a git repository: `Error: not a git repository (or any parent). SDI requires git.`
- Git not installed: `Error: git not found in PATH`
- Python version too old: caught at install time, not runtime

**Analysis errors (exit code 3):**
- Tree-sitter grammar not available for a detected language: `WARN` (not fatal). `Warning: no tree-sitter grammar for 'kotlin' — skipping 23 files. Install with: pip install tree-sitter-kotlin`
- All languages unsupported: `ERROR` + exit 3. `Error: no supported languages found in repository`
- Graph too small for meaningful clustering: `WARN`. Proceeds with partial metrics.

**Runtime errors (exit code 1):**
- Unexpected exceptions: caught at top level, traceback printed only in `DEBUG` mode. User sees: `Error: unexpected failure during pattern analysis. Run with SDI_LOG_LEVEL=DEBUG for details.`

**Threshold exceeded (exit code 10, `sdi check` only):**
- One or more SDI dimensions exceeded configured thresholds. Prints which dimensions exceeded and by how much. This distinct exit code allows CI scripts to distinguish "drift too high" from "tool broke" without parsing output.

### Verbosity Levels

| Level | Behavior |
|---|---|
| `ERROR` | Only errors |
| `WARN` | Warnings and errors |
| `INFO` (default) | Progress bar during parsing, summary stats after each stage |
| `DEBUG` | Tree-sitter parse timings per file, graph construction details, Leiden iteration count, partition stability details, pattern matching internals |

Controlled via `SDI_LOG_LEVEL` environment variable or `--debug` flag.

## Shell Integration

### Git Hook Integration

Git hooks are the primary integration point for SDI.

**Post-merge hook**: `sdi init` offers to install a post-merge git hook that runs `sdi snapshot` automatically on every merge to the configured branch. The hook script is a thin shell wrapper: checks the branch, runs `sdi snapshot --quiet`, and exits 0 always — hook failure should never block merges.

**Pre-push hook** (opt-in): `sdi check` as a pre-push hook, exits non-zero to block pushes that would exceed drift thresholds. Opt-in only, not installed by default.

Hook installation is non-destructive: appends to existing hooks or creates new ones.

### CI Integration

**Generic CI**: `sdi check` with exit codes is the universal integration point. Any CI system that can run a command and check exit codes can gate on structural drift:

```bash
pip install sdi
sdi check
```

**GitHub Actions**: A reusable action (`sdi-action`) that runs `sdi snapshot` + `sdi check` and posts a summary comment on PRs with drift deltas is a stretch goal, not v1. Document manual CI integration for v1.

### Tab Completion

Click provides built-in shell completion generation for bash, zsh, and fish. Installed via the standard Click pattern:

```bash
# bash
eval "$(_SDI_COMPLETE=bash_source sdi)"

# zsh
eval "$(_SDI_COMPLETE=zsh_source sdi)"

# fish
_SDI_COMPLETE=fish_source sdi | source
```

### Piping Support

All JSON and CSV output is designed for downstream consumption:

```bash
sdi show --format json | jq '.pattern_catalog'
sdi trend --format csv | head -20
sdi diff --format json | jq '.boundary_violations'
```

### Signal Handling

| Signal | Behavior |
|---|---|
| `SIGINT` (Ctrl+C) | Clean shutdown. If mid-snapshot, discard incomplete snapshot file (atomic write via tempfile + rename means partial snapshots never exist). |
| `SIGTERM` | Same as `SIGINT`. |
| `SIGHUP` | No special handling (not a daemon). |

### Color Output

- Respects `NO_COLOR` environment variable ([no-color.org](https://no-color.org) convention)
- `--no-color` flag overrides
- Auto-detection: color when stderr/stdout is a TTY, plain when piped
- Rich library handles all color and formatting

### Progress Indicators

- **File parsing**: Rich progress bar on stderr (`Parsing files [143/892] ...`)
- **Graph analysis**: Spinner on stderr (`Building dependency graph...`)
- Suppressed when `--quiet` is set or when stderr is not a TTY

## File System Operations

### Directory Structure

Created by `sdi init`:

```
.sdi/
├── config.toml          # Project configuration (user-editable, committed to VCS)
├── boundaries.yaml      # Ratified boundary spec (user-editable, committed to VCS)
├── snapshots/           # Snapshot JSON files (committed to VCS)
│   └── <timestamp>-<short-sha>.json
└── cache/               # Internal caches (gitignored)
    ├── partition.json   # Last Leiden partition for seeding
    ├── parse_cache/     # Tree-sitter parse results keyed by file content hash
    └── fingerprints/    # Pattern fingerprint hashes keyed by file content hash
```

### VCS Policy

| Path | VCS Status | Rationale |
|---|---|---|
| `.sdi/config.toml` | Committed | Shared project configuration |
| `.sdi/boundaries.yaml` | Committed | Ratified architectural intent — reviewable in git history |
| `.sdi/snapshots/` | Committed | Structural health record — teams review snapshot history alongside code changes |
| `.sdi/cache/` | Gitignored | Ephemeral acceleration data; `sdi init` adds `.sdi/cache/` to `.gitignore` |

### Atomic Writes

All file creation uses `tempfile` in the target directory + `os.replace()` (atomic rename on POSIX). A crash or SIGINT mid-write never produces a partial snapshot or corrupted config. Snapshot filenames include timestamp and short SHA, so concurrent runs (unlikely but possible in CI) produce distinct files rather than overwriting.

### Temporary Files

Created in the target directory (same filesystem for atomic rename guarantee) via Python's `tempfile` module. Cleaned up on normal exit and in signal handlers. Stale tempfiles from hard kills have random suffixes and do not interfere with operation.

### Lock Files

None in v1. SDI operations are idempotent — running two snapshots concurrently produces two snapshot files, both valid. The cache directory uses content-addressed filenames (hash-keyed) so concurrent writes do not conflict.

### File Permissions

Default umask. No special permission handling — SDI operates within the user's normal permissions context.

### Snapshot Retention

`sdi snapshot` enforces the configured retention limit (default: 100). After writing a new snapshot, if the snapshot count exceeds the limit, the oldest snapshots are deleted. This keeps `.sdi/snapshots/` bounded without manual cleanup.

## Performance & Resource Usage

### Performance Targets

These targets are hard requirements for CI viability:

| Codebase Size | Files | Target |
|---|---|---|
| Small (< 10K LOC) | ~100 | < 5 seconds |
| Medium (10K–100K LOC) | ~1,000 | < 30 seconds |
| Large (100K–500K LOC) | ~5,000 | < 2 minutes |
| Very large (500K+ LOC) | 5,000+ | Best-effort; may require exclude patterns to stay under 5 minutes |

### Performance Breakdown by Stage (Medium Project)

| Stage | Estimated Time | Bottleneck |
|---|---|---|
| Tree-sitter parsing | 2–5 seconds | File I/O (native parsing is 1M+ lines/sec) |
| Dependency graph construction | < 1 second | In-memory graph building |
| Leiden community detection | < 1 second (seeded), 2–5 seconds (cold start) | igraph C backend, 2–5 iterations to converge |
| Pattern fingerprinting | 1–5 seconds | AST query traversal, proportional to pattern count |
| Snapshot assembly + delta | < 1 second | JSON serialization + graph comparison |

### Memory Usage

- **Tree-sitter CSTs**: Parsed per-file with features extracted immediately. Full CSTs are NOT held in memory simultaneously — parse, extract, discard. Memory is proportional to the largest single file, not total codebase size.
- **Dependency graph**: Held entirely in memory via igraph. For 5,000-node graphs this is negligible (< 50MB). For very large monorepos (50K+ files) this could reach hundreds of MB — documented as a known scaling limit.
- **Pattern fingerprints**: Hash-based with constant memory per pattern instance.

### Caching Strategy

**Parse cache**: Keyed by file content hash (SHA-256 of file bytes). If a file hasn't changed since the last run, extracted features are reused from `.sdi/cache/parse_cache/`. This makes incremental snapshots (few files changed since last run) near-instant for the parsing stage.

**Partition cache**: Previous Leiden partition stored in `.sdi/cache/partition.json`. Seeding from this makes subsequent community detection runs faster and more stable.

**Cache invalidation**: Content-addressed (hash-keyed) so stale entries are naturally orphaned. Periodic cleanup on `sdi snapshot` removes orphaned cache entries older than the configured retention window.

### Parallelism

File parsing uses `concurrent.futures.ProcessPoolExecutor`. Worker count defaults to `os.cpu_count()` but is configurable via the `SDI_WORKERS` environment variable. Graph operations are single-threaded (igraph limitation) but fast enough that parallelism is unnecessary.

## Versioning & Compatibility

### Versioning Scheme

Semantic versioning (semver): MAJOR.MINOR.PATCH.

### Pre-1.0 (0.x.y)

No stability guarantees. CLI flags, config keys, snapshot schema, and boundary spec format may all change between minor versions. This is explicitly a prototype and validation phase. The snapshot schema will evolve as the team learns what measurements are actually useful in practice.

### Post-1.0 Stability Guarantees

**CLI interface**: Flags and commands are stable across minor versions. New commands and flags may be added. Existing flags are never removed or have their semantics changed without a major version bump. Deprecation warnings appear for at least one minor version before removal.

**Snapshot JSON schema**: Versioned via a `snapshot_version` field in every snapshot file. SDI can read snapshots from older schema versions for trend computation. Schema changes that would break backward-readable compatibility require a major version bump.

**Config file**: Versioned implicitly. New config keys are additive with defaults — old config files continue to work. Removed keys are silently ignored with a deprecation warning. Config keys are never repurposed (a removed key is reserved forever).

**Boundary spec**: Versioned via a `version` field. Same backward-compatibility rules as snapshot schema.

**Exit codes**: The semantics of exit codes 0, 1, 2, 3, and 10 are stable across all versions, including pre-1.0.

### Core Guarantees (Post-1.0)

- `sdi snapshot` always produces a valid snapshot file readable by the same or later version
- `sdi diff` and `sdi trend` can always read snapshots from the same major version
- Exit code semantics are stable across all versions

## Distribution & Installation

### PyPI (Primary)

```bash
pip install sdi
```

Installs the `sdi` command-line entry point. Pulls tree-sitter, leidenalg, and igraph as dependencies. Tree-sitter grammar packages are installed separately per-language:

```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
```

Convenience bundles under consideration:

| Extra | Languages | Install Command |
|---|---|---|
| `[all]` | All supported grammars | `pip install sdi[all]` |
| `[web]` | Python + TypeScript + JavaScript | `pip install sdi[web]` |
| `[systems]` | Go + Rust + C | `pip install sdi[systems]` |

### Homebrew

```bash
brew tap geoffgodwin/sdi
brew install sdi
```

Formula in a separate `homebrew-sdi` tap repository. Handles Python dependency isolation via Homebrew's Python virtualenv conventions. Includes the most common grammar packages.

### Build from Source

```bash
git clone https://github.com/GeoffGodwin/sdi.git
cd sdi
pip install -e ".[dev]"
```

Requires Python 3.10+.

### Platform Support

| Platform | Support Level |
|---|---|
| Linux | Primary development and CI platform |
| macOS | Tested in CI, Homebrew formula ensures compatibility |
| Windows | Best-effort. tree-sitter and igraph have Windows wheels. leidenalg may require a C compiler — documented. Not blocking for v1. |

### System Requirements

- Python 3.10+
- `git` must be in `PATH` (SDI shells out to git for history analysis)
- No other system dependencies — tree-sitter, igraph, and leidenalg all distribute pre-built wheels for major platforms

### Update Mechanism

Manual only in v1: `pip install --upgrade sdi` or `brew upgrade sdi`. No self-update command. A version check on `sdi --version` that prints a notice if a newer version is available on PyPI is under consideration, but this requires a network call so it would be opt-in only and off by default (respecting the "no network calls" philosophy).

## Testing Strategy

### Testing Framework

pytest with pytest-cov for coverage reporting. Coverage target: 80%+ for unit tests. Integration tests are not coverage-gated but must all pass.

### Unit Tests (tests/unit/)

| Area | What Is Tested |
|---|---|
| Pattern fingerprinting | Structurally equivalent AST subtrees produce identical fingerprints; structurally different ones produce different fingerprints. Tested across multiple languages. |
| Dependency graph construction | Given known import relationships, verify correct graph edges. Each language adapter tested independently. |
| Snapshot delta computation | Given two snapshot JSON objects, verify correct computation of all four SDI dimensions. |
| Leiden partition stability | Seeded partitions are stable when graph changes are small, and update correctly when changes are large. |
| Config loading | Verify precedence order, default values, invalid config handling. |
| Boundary spec parsing | Verify YAML parsing, validation of required fields, handling of aspirational splits. |

### Integration Tests (tests/integration/)

- **Full pipeline tests**: Run `sdi snapshot` against fixture repos and verify snapshot output matches expected structure and values.
- **Multi-snapshot workflows**: `init` → `snapshot` → modify fixture → `snapshot` → `diff` → `trend`. Verify the full lifecycle produces correct deltas.
- **CLI output tests**: Snapshot stdout/stderr output for each command and compare against expected output (pytest-snapshot or similar).
- **Git hook integration**: Verify hook installation and that the post-merge hook triggers snapshot capture correctly.

### Fixture Repos (tests/fixtures/)

| Fixture | Purpose |
|---|---|
| `tests/fixtures/simple-python/` | Small Python project with known dependency structure, one deliberate pattern variant (two error handling styles), and one boundary crossing. Baseline for most integration tests. |
| `tests/fixtures/multi-language/` | Python + TypeScript files. Tests cross-language dependency graph construction and language adapter integration. |
| `tests/fixtures/high-entropy/` | Deliberately high pattern entropy (4+ error handling styles, 3 data access patterns). Tests pattern fingerprinting accuracy and entropy computation. |
| `tests/fixtures/evolving/` | Git repo with multiple commits that introduce progressive structural drift. Used for trend and diff testing. Created by a setup script that builds the git history programmatically. |

### Platform Testing

CI matrix: Linux (Ubuntu latest) + macOS (latest). Python 3.10, 3.11, 3.12. Windows is not in the CI matrix for v1, documented as best-effort.

### Performance Benchmarks

`tests/benchmarks/` contains pytest-benchmark tests for the parsing stage and Leiden detection on synthetic graphs of increasing size (100, 1,000, 5,000, 10,000 nodes). Tracks regression across releases. Not run in normal CI — triggered manually or on release tags.

## Naming Conventions

### Code Naming (Python)

PEP 8 throughout:

| Element | Convention | Example |
|---|---|---|
| Functions, variables, modules | `snake_case` | `compute_entropy`, `parse_cache` |
| Classes | `PascalCase` | `PatternFingerprint`, `BoundarySpec` |
| Module-level constants | `UPPER_SNAKE` | `DEFAULT_GAMMA`, `MAX_RETENTION` |

Type hints on all public function signatures. No type hints on local variables unless the type is non-obvious. Docstrings on all public functions and classes (Google style).

### Module Structure

```
sdi/
├── cli/           # Click command definitions
├── parsing/       # Tree-sitter parsing + language adapters
│   ├── python.py
│   ├── typescript.py
│   └── ...
├── graph/         # Dependency graph construction
├── detection/     # Leiden community detection, boundary management
├── patterns/      # Pattern fingerprinting, catalog
├── snapshot/      # Snapshot model, assembly, delta computation
└── config.py      # Configuration loading
```

One class per file is NOT required — group related functionality by module.

### Command and Flag Naming

- **Subcommands**: Single words only (`init`, `snapshot`, `diff`, `trend`, `check`, `show`, `boundaries`, `catalog`). No multi-word commands.
- **Long flags**: `--kebab-case` (`--no-color`, `--format`, `--last`, `--output`)
- **Short flags**: Single letter for the most common flags only (`-o` for `--output`, `-f` for `--format`, `-n` for `--last`, `-v` for `--verbose`, `-q` for `--quiet`)
- **Boolean flags**: `--flag` to enable, `--no-flag` to disable (Click convention)

### Environment Variables

Prefix `SDI_` with `UPPER_SNAKE_CASE` (e.g., `SDI_CONFIG_PATH`, `SDI_LOG_LEVEL`, `SDI_WORKERS`). Exception: `NO_COLOR` uses no prefix per industry standard.

### Domain Term → Code Concept Mapping

| Domain Term | Code Concept | Module |
|---|---|---|
| Snapshot | `Snapshot` dataclass | `sdi.snapshot.model` |
| Boundary | `BoundarySpec` / `BoundaryModule` | `sdi.detection.boundaries` |
| Pattern | `PatternInstance` / `PatternFingerprint` | `sdi.patterns.fingerprint` |
| Catalog | `PatternCatalog` (dict: category → list of fingerprints) | `sdi.patterns` |
| Partition | igraph `VertexClustering` object | Leiden output |
| Divergence | `DivergenceSummary` dataclass (four SDI dimensions) | `sdi.snapshot` |
| Drift rate | `float` (delta / interval, always a rate not an absolute) | Computed in delta stage |

## Config Architecture

### Values That Must Live in Config

These values are project-specific and must never be hardcoded:

- Leiden gamma parameter (teams must tune to their project's graph structure)
- Drift rate thresholds for `sdi check` (acceptable drift varies by project)
- Snapshot retention count (disk space implications)
- Exclude patterns (project-specific ignore rules beyond `.gitignore`)
- Change coupling history depth and minimum frequency (analysis tuning knobs)
- Pattern categories (must be extensible beyond the built-in catalog)
- Per-category threshold overrides with expiry dates (migration intent declarations)

### Values That Are Hardcoded

- Snapshot JSON schema version (tied to code version, not tunable)
- Exit code semantics (0, 1, 2, 3, 10 — part of the public API contract)
- `.sdi/` directory name (convention, not configurable)
- Tree-sitter query patterns per language (shipped with the tool, not user-editable in v1)

### Complete Default Configuration

See the [Configuration System](#configuration-system) section for the full default configuration with every key and its default value.

### Override Hierarchy

Highest to lowest precedence:

1. **CLI flags** (`--format json`, `--no-color`, etc.)
2. **Environment variables** (`SDI_LOG_LEVEL`, `SDI_WORKERS`, `SDI_CONFIG_PATH`, `NO_COLOR`)
3. **Project-local config** (`.sdi/config.toml` in repo root)
4. **Global user config** (`~/.config/sdi/config.toml`)
5. **Built-in defaults** (hardcoded in `sdi/config.py`)

### Reset to Defaults

Delete `.sdi/config.toml` and run `sdi init` to regenerate with commented defaults. Alternatively, remove specific keys from the file — missing keys fall through to built-in defaults.

## Open Design Questions

### 1. Weighted vs. Unweighted Edges in the Dependency Graph

Should import frequency (number of symbols imported) affect edge weight in Leiden community detection? Weighted edges might improve cluster quality by distinguishing a single type import from a module that imports 20 symbols. But they might also introduce noise if a utility module is heavily imported everywhere. The default is unweighted. This needs empirical testing across real codebases. Exposed as a config toggle (`weighted_edges`) to let users experiment.

**Information needed to resolve**: Benchmark Leiden partition quality (measured by modularity and human agreement) on 3–5 real codebases with weighted vs. unweighted edges.

### 2. Resolution Parameter Auto-Tuning

Leiden's gamma parameter controls cluster granularity. The default (1.0) works for many graphs but may produce too few clusters on large codebases or too many on small ones. Should SDI auto-tune gamma based on graph density, or is a static default with manual override sufficient? Auto-tuning adds complexity and reduces reproducibility. Deferring to manual config for v1 and collecting data on what gamma values real projects use.

**Information needed to resolve**: Gamma values chosen by early adopters across projects of different sizes and structures.

### 3. Pattern Category Extensibility Mechanism

V1 ships with a built-in catalog of pattern categories and tree-sitter queries per language. Users will want to define custom categories. The mechanism is TBD: tree-sitter query files in `.sdi/`? A Python plugin interface? A TOML-based pattern definition DSL? Real user feedback is needed on what categories people want before designing the extensibility API.

**Information needed to resolve**: Feature requests from early users indicating what custom categories they need and how they would prefer to define them.

### 4. Multi-Language Dependency Resolution in Monorepos

When a TypeScript frontend imports from a Python backend via an API contract, that is a cross-language dependency that does not appear in import statements. How (or whether) to model these implicit dependencies is an open question. V1 only tracks explicit in-language imports. Cross-language coupling detection is deferred.

**Information needed to resolve**: Survey of common cross-language integration patterns and whether OpenAPI specs or protobuf definitions could serve as a dependency source.

### 5. Snapshot Storage Scaling

At 100 snapshots retained with JSON files of ~10–50KB each, storage is trivial. But some teams might want years of history (1,000+ snapshots). Should there be a compact binary format? A SQLite store? Deferred — JSON files with retention limits are sufficient for v1 and the simplicity is worth preserving.

**Information needed to resolve**: Real-world snapshot sizes and retention requirements from early adopters.

### 6. YAML Library Choice for Boundary Specs

PyYAML is ubiquitous but loses comments on round-trip. ruamel.yaml preserves comments but is a heavier dependency with a more complex API. Since boundary specs are human-edited artifacts where comments carry architectural rationale, comment preservation matters. Currently leaning ruamel.yaml but need to evaluate install friction on all platforms.

**Information needed to resolve**: Platform compatibility testing for ruamel.yaml, particularly on Windows and in CI environments.

### 7. Generated/Vendored Code Handling

Files in `vendor/` or `generated/` directories are excluded by default, but what about generated code that lives alongside handwritten code (e.g., protobuf stubs, ORM models)? These affect the dependency graph and pattern catalog but were not authored by humans or agents. A mechanism is needed to tag files or directories as "generated" so they can be optionally excluded from pattern entropy calculations while still being included in dependency graph construction.

**Information needed to resolve**: Common patterns for generated code placement across ecosystems and whether a `.sdi/generated.glob` file or inline annotations are more practical.

### Resolved Design Decisions

**R1. Drift vs. Evolution: Measure, Don't Classify.**

The question "is this drift or intentional evolution?" is central to SDI's value proposition. The rejected approach was automatic classification — having SDI infer from pattern velocity vectors and boundary-locality whether a change is a "migration" or "drift" and suppressing alerts accordingly. This was rejected because it violates principles #1 (classification requires heuristic thresholds that are opinions, not measurements) and #3 (the tool would be deciding what changes are acceptable, which is a human judgment). It also creates dangerous false negatives in CI gates.

The adopted approach has two parts:

1. SDI computes and reports per-shape velocity (instance count delta) and per-shape boundary spread (boundary count) as raw measurements. These appear in `sdi diff` and `sdi trend` output so humans can see whether opposing velocity vectors suggest a migration is underway.
2. Teams declare migration intent via per-category threshold overrides with expiry dates in `config.toml` (`[thresholds.overrides.<category>]`). This mirrors the boundary ratification pattern: explicit, auditable, time-boxed, committed to VCS. When the override expires, default thresholds resume — forcing a conversation if the migration stalled.

## What Not to Build Yet

### IDE/Editor Plugin

CLI first. An IDE integration that shows real-time boundary violations or pattern drift inline would be valuable, but requires a stable API and snapshot format. **Evaluate after v1.0** when the schema is stable.

### SaaS Dashboard / Web UI

The indexer is a measurement instrument, not a platform. The output is JSON and text that can be consumed by existing dashboards (Grafana, Datadog, custom). Building a hosted UI is a different product. If there is demand, it would be a separate project that reads SDI snapshots.

### Auto-Remediation / Gardener Agent

SDI's job is to detect and measure drift, not fix it. A companion tool that reads SDI output and generates PRs to consolidate pattern variants is a logical follow-on but out of scope for the measurement instrument itself.

### GitHub Actions Marketplace Action

Document manual CI integration in v1 (`pip install sdi && sdi check`). A polished reusable action with PR comments, badge generation, and trend graphs is a **post-v1 deliverable**.

### Plugin System for Custom Analyzers

V1 ships built-in pattern categories only. A plugin interface for user-defined tree-sitter queries and custom metrics requires a stable internal API. **Design the extensibility point after real users provide feedback** on what they need.

### Cross-Language Dependency Inference

Detecting implicit dependencies between services (TypeScript frontend calling Python API) requires understanding API contracts, OpenAPI specs, or protobuf definitions. This is a significant scope expansion. **V1 tracks only explicit in-language imports.**

### Historical Backfill

Running SDI retroactively across hundreds of past commits to generate a historical trend line is technically possible (`sdi snapshot --commit REF`) but the UX for batch backfill (parallelism, progress, storage) is not designed yet. Users can script it with a bash loop in v1.

### Standalone Binary Distribution

PyInstaller or Nuitka packaging for users who don't want Python installed. **Evaluate after the dependency tree stabilizes.** Tree-sitter grammar loading from bundled binaries has known complexity.

### Real-Time / Watch Mode

A daemon that monitors file changes and updates metrics continuously violates the Unix philosophy constraint and adds significant complexity (file watchers, incremental graph updates). CLI invocation on merge events is the intended cadence.

### Automatic Drift-vs-Evolution Classification

SDI will never automatically classify pattern changes as "drift" or "migration" or suppress alerts based on inferred intent. This was considered and explicitly rejected (see Resolved Design Decision R1) because it requires opinionated heuristics and creates false negatives in CI gates. SDI reports the raw measurements that make the distinction visible to humans, and teams declare migration intent via threshold overrides. If future versions add classification, it would be an opt-in advisory annotation, never a gate-suppression mechanism.
