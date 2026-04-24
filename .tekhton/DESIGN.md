# Design Document — Structural Divergence Indexer (SDI)

## Developer Philosophy & Constraints

SDI is built on a set of non-negotiable architectural principles that govern every design decision, every line of code, and every contributor interaction. These principles exist because SDI occupies a unique position in the developer tooling ecosystem: it is a measurement instrument for structural coherence, not an opinion engine. Violating any of these principles undermines the tool's core value proposition.

### Core Principles

**Measurement over opinion.** Every claim SDI makes about a codebase must be backed by a concrete, reproducible measurement derived from AST analysis or dependency graph structure. No heuristics that cannot be explained. No scores without traceable inputs. If a metric cannot be decomposed into its constituent measurements, it does not ship. Pattern entropy is a count of distinct structural shapes — not a quality score. Boundary violation velocity is a rate of new cross-boundary dependencies — not a judgment about whether those dependencies are acceptable.

**Fever chart, not thermometer.** Every metric SDI produces must be trackable over time. Point-in-time values are necessary but insufficient. The primary output is always the trend: the rate of change of structural coherence, not the absolute state. Alerts fire on rate-of-change thresholds, not absolute values. A codebase with high pattern entropy that has been stable for months is not alarming; a codebase with moderate entropy that doubled in two weeks demands attention.

**Automated inference, human ratification.** SDI never tells a team what their architecture "should" be. It infers structural boundaries from the code via Leiden community detection, proposes them, and waits for a human to ratify, merge, split, or override. The tool measures divergence from declared intent, not from its own opinions. Pattern categories detect structural shapes and count them but never classify code as "good" or "bad."

**Safe defaults, zero mandatory config.** Running `sdi snapshot` on an un-initialized repository produces useful output using purely inferred boundaries and auto-detected patterns. Configuration refines and ratifies — it is never required for first use. A developer encountering SDI for the first time should get value from a single command without reading any documentation about configuration.

**Composable Unix tooling.** SDI reads from the filesystem and git history, writes JSON snapshots and human-readable reports to stdout/files, and exits with meaningful codes. It composes with `jq`, `diff`, CI pipelines, and git hooks. No daemon mode, no server, no interactive TUI in v1. Every output is designed to be piped, redirected, or consumed by another tool.

**Language-agnostic core, language-specific adapters.** The dependency graph, community detection, pattern fingerprinting, and snapshot diffing are language-agnostic. Language specifics — import resolution, AST queries for pattern categories — live in adapter modules that can be added independently. Tree-sitter provides a consistent AST representation across all supported languages.

**Deterministic and reproducible.** Given the same commit, the same configuration, and the same boundary spec, SDI produces the same snapshot. The Leiden algorithm is seeded from the previous partition for stability; cold-start runs use a fixed random seed (default: 42) so that first-run results are reproducible across machines and CI environments.

**Fast enough for CI.** A snapshot capture must complete in seconds to low minutes on codebases up to 500K lines. This is a hard constraint — SDI runs on every merge to the primary branch. Tree-sitter parsing is already fast; the budget concern is graph analysis on large dependency graphs.

**Drift vs. evolution is measured, not classified.** SDI computes the second-order signals that distinguish incoherent structural drift from intentional architectural migration — pattern velocity vectors (instance count deltas per shape across snapshots) and boundary-locality (how many boundaries a pattern variant spans). These are objective measurements reported in the snapshot. The tool never classifies a change as "drift" or "migration" — that is a human judgment. Teams declare migration intent through per-category threshold overrides with expiry dates.

### Banned Anti-Patterns

| Anti-Pattern | Rationale | Enforcement |
|---|---|---|
| ML/LLM calls in the analysis pipeline | SDI is a measurement instrument; determinism and reproducibility are non-negotiable | Code review gate |
| Network calls during analysis | Everything operates on local filesystem and git history; a snapshot must be producible on an airgapped machine | Code review gate |
| Opinions about code quality | SDI measures structural divergence, not whether code is "good" or "bad"; a high pattern entropy might be acceptable | Code review gate |
| Automatic alert suppression | SDI never decides that elevated metrics are acceptable; teams must declare intent via threshold overrides with expiry dates | Config validation (missing `expires` field = exit code 2) |
| Interactive TUI or daemon mode | CLI invocation only; run, produce output, exit | Architectural constraint |

## Project Overview

SDI (Structural Divergence Indexer) is a CLI tool that computes and tracks the Structural Divergence Index — a composite metric measuring the rate of structural drift in a codebase across four dimensions: pattern entropy, convention drift rate, coupling topology delta, and boundary violation velocity. The metric is the Structural Divergence Index; the tool is the Structural Divergence Indexer.

SDI captures periodic structural fingerprints (snapshots) via tree-sitter AST parsing and Leiden community detection, diffs them over time, and produces trend data and actionable CI gate checks. Each snapshot records the structural shape of a codebase at a point in time. The delta between snapshots reveals how the codebase's structure is changing. The trend across many snapshots reveals whether those changes are coherent or divergent.

### Target Users

Software engineers, tech leads, and engineering managers responsible for the structural health of codebases — particularly teams using AI-assisted development at scale where multiple independent contributors (human or agent) generate code concurrently without shared structural awareness. SDI fills the observability gap between individual code review (which evaluates changes in isolation) and architectural governance (which operates at project timescales).

### What It Replaces

There is no existing tool that does what SDI does. Current quality tooling — linters, static analyzers, code review — evaluates individual changes in isolation. The Structural Divergence Index fills the gap between "every individual change is good" and "the collective direction of all changes is coherent." SDI is the urban planner's aerial photograph overlaid on the master plan, complementing the building inspector (linter) and structural engineer (static analyzer) that already exist.

### Distribution Model

Open source under MIT or Apache 2.0. The tool and its output format are public goods — the value proposition is the measurement methodology, not proprietary analysis.

### Invocation Frequency

Typically once per merge to the primary integration branch. High-velocity teams might run it 10–50 times per day. CI integration is the primary use case, with manual invocation for exploration and debugging.

## Tech Stack

### Language

**Python 3.10+.** Tree-sitter has mature Python bindings (tree-sitter 0.24+), the Leiden algorithm has a maintained Python package (leidenalg by V.A. Traag), igraph has a mature Python interface for graph analysis, and Python is the lingua franca for developer tooling that interacts with AST parsing. Performance-critical paths (tree-sitter parsing, igraph graph operations) are backed by C/C++ libraries, so Python overhead is negligible for the orchestration layer.

### Key Dependencies

| Package | Purpose | Version Constraint |
|---|---|---|
| tree-sitter | Multi-language AST parsing | >=0.24 |
| tree-sitter-python, tree-sitter-javascript, tree-sitter-typescript, tree-sitter-go, tree-sitter-java, tree-sitter-rust | Per-language grammar packages | Per grammar |
| leidenalg | Leiden community detection algorithm | Latest stable |
| igraph | Graph construction, analysis, cycle detection, centrality | Latest stable |
| click | CLI framework (argument parsing, subcommands, help) | Latest stable |
| rich | Terminal output formatting (tables, progress bars, color) | Latest stable |
| tomli / tomllib | TOML config parsing (tomllib is stdlib in 3.11+, tomli for 3.10) | tomli for 3.10 compat |
| tomli-w | TOML writing for `sdi init` config generation | Latest stable |
| ruamel.yaml | YAML parsing for boundary specs (preserves comments) | Pending validation (see Open Design Questions) |

### Serialization

- **JSON** for snapshot files (stdlib `json` module). Universal readability, composable with `jq`, and snapshot sizes (10–50KB) make storage trivial.
- **TOML** for configuration (`.sdi/config.toml`). Python ecosystem standard with clear semantics.
- **YAML** for boundary specifications (`.sdi/boundaries.yaml`). Boundary specs are lists-of-objects with comments carrying architectural rationale — YAML's comment support and list syntax are better suited than TOML for this artifact.

### Testing Framework

pytest with pytest-cov for coverage reporting. pytest-benchmark for performance regression tests on release tags. Fixture repos (small synthetic codebases with known structural properties) for integration tests.

### Build and Distribution

Standard Python packaging with `pyproject.toml` (PEP 621). hatchling or setuptools as build backend.

| Channel | Command | Notes |
|---|---|---|
| PyPI (primary) | `pip install sdi` | Core install; grammar packages separate |
| PyPI extras | `pip install sdi[all]` | Convenience bundle with all grammars |
| Homebrew | `brew tap geoffgodwin/sdi && brew install sdi` | Separate tap repo |
| Source | `git clone` + `pip install -e ".[dev]"` | Requires Python 3.10+ |

Binary releases via PyInstaller or Nuitka are a stretch goal, not v1.

## Command Taxonomy

SDI is a multi-command CLI (git-style). The root command is `sdi`. All commands share global flags: `--format`, `--no-color`, `--quiet`, `--verbose`.

### sdi init

**Syntax:** `sdi init [--force] [--language LANG]...`

**Description:** Initialize SDI configuration in the current repository. Creates the `.sdi/` directory with default config, runs initial structural inference to propose boundaries, and optionally writes a starter boundary spec for ratification.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--force` | boolean | false | Overwrite existing `.sdi/` configuration |
| `--language` | string (repeatable) | auto-detect | Explicitly specify languages to analyze |

**Examples:**
```bash
sdi init
sdi init --language python --language typescript
sdi init --force
```

### sdi snapshot

**Syntax:** `sdi snapshot [--output PATH] [--commit REF] [--format json|summary]`

**Description:** Capture the current structural fingerprint of the codebase. Parses source via tree-sitter, builds the dependency graph, runs Leiden community detection (seeded from previous partition if available), computes all four SDI dimensions, and writes a snapshot file.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--output`, `-o` | path | `.sdi/snapshots/<timestamp>-<short-sha>.json` | Write snapshot to specific path |
| `--commit` | git ref | HEAD (working tree) | Analyze a specific git commit instead of working tree |
| `--format`, `-f` | `json` or `summary` | json + summary | Output format |

**Examples:**
```bash
sdi snapshot
sdi snapshot --commit HEAD~5
sdi snapshot --output /tmp/baseline.json --format json
```

**Note:** When `--commit` is specified, SDI reads files at that commit via `git show REF:path` or `git archive`. It never runs `git checkout` or modifies the working tree.

### sdi diff

**Syntax:** `sdi diff [SNAPSHOT_A] [SNAPSHOT_B] [--format json|text]`

**Description:** Compare two snapshots and show what changed structurally. If no arguments are given, compares the two most recent snapshots. If one argument is given, compares it against the most recent.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--format`, `-f` | `text` or `json` | text | Output format |

**Examples:**
```bash
sdi diff
sdi diff .sdi/snapshots/20260401-a1b2c3d.json .sdi/snapshots/20260403-d4e5f6a.json
sdi diff --format json
```

### sdi trend

**Syntax:** `sdi trend [--last N] [--dimension DIMENSION] [--format text|json|csv]`

**Description:** Show trend data across multiple snapshots. Displays the trajectory of each SDI dimension over time — the fever chart.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--last`, `-n` | integer | 20 | Number of most recent snapshots to include |
| `--dimension` | enum | all | Filter to a specific dimension |
| `--format`, `-f` | `text`, `json`, or `csv` | text | Output format |

Valid dimension values: `pattern_entropy`, `convention_drift`, `coupling_topology`, `boundary_violations`.

**Examples:**
```bash
sdi trend
sdi trend --last 50 --dimension pattern_entropy
sdi trend --format csv > metrics.csv
```

### sdi check

**Syntax:** `sdi check [--threshold FLOAT] [--dimension DIMENSION] [--snapshot PATH]`

**Description:** CI-friendly gate. Captures a snapshot (or uses a provided one), computes drift rates against recent history, and exits non-zero if any rate exceeds the configured threshold. Designed for use in CI pipelines and git hooks.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--threshold` | float | from config | Override drift rate threshold |
| `--dimension` | enum | all | Check only a specific dimension |
| `--snapshot` | path | (captures new) | Use an existing snapshot instead of capturing |

**Exit codes:**

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

**Syntax:** `sdi show [--format text|json] [--verbose]`

**Description:** Human-readable summary of the current state. Shows the most recent snapshot data, current boundary map, pattern catalog summary, and any active alerts. This is the "what does my codebase look like right now" command.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--format`, `-f` | `text` or `json` | text | Output format |
| `--verbose`, `-v` | boolean | false | Include full pattern catalog and boundary details |

**Examples:**
```bash
sdi show
sdi show --verbose
sdi show --format json | jq '.pattern_catalog'
```

### sdi boundaries

**Syntax:** `sdi boundaries [--propose] [--ratify] [--export PATH] [--format text|yaml]`

**Description:** View, propose, or manage architectural boundary definitions. Without flags, shows the current ratified boundary map. With `--propose`, runs Leiden inference and shows proposed changes. With `--ratify`, opens the boundary spec in `$EDITOR` for ratification after reviewing a proposal.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--propose` | boolean | false | Run inference and show proposed boundary map |
| `--ratify` | boolean | false | Open boundary spec in `$EDITOR` for ratification |
| `--export` | path | (none) | Export current boundary map to a file |
| `--format`, `-f` | `text` or `yaml` | text | Output format for display |

**Examples:**
```bash
sdi boundaries
sdi boundaries --propose
sdi boundaries --propose --ratify
sdi boundaries --export /tmp/boundaries.yaml
```

### sdi catalog

**Syntax:** `sdi catalog [--category CATEGORY] [--format text|json]`

**Description:** View the detected pattern catalog — all structural fingerprints grouped by operation category. Shows which patterns exist, how many variants of each, and which is marked canonical.

| Flag | Type | Default | Description |
|---|---|---|---|
| `--category` | string | all | Filter to a specific pattern category |
| `--format`, `-f` | `text` or `json` | text | Output format |

**Examples:**
```bash
sdi catalog
sdi catalog --category error_handling --format json
```

## Input Sources & Formats

SDI reads from five input sources, each serving a distinct purpose in the analysis pipeline. No input source requires network access — all data is local.

### Source Code Files

SDI reads source code files via tree-sitter parsing. V1 targets six languages: Python, TypeScript, JavaScript, Go, Java, and Rust. Additional languages are added by installing the corresponding tree-sitter grammar package.

File discovery walks the repository file tree, filtering by `.gitignore` rules and configured exclude patterns. Language detection is performed by file extension with fallback to tree-sitter grammar probing. Files for which no grammar is available are skipped with a warning — they do not block the snapshot.

### Git History

SDI shells out to `git` for change coupling analysis, commit-to-snapshot association, and convention drift rate computation. It reads `git log`, `git diff`, and `git show` output. A git repository is required — running SDI outside a git repo produces exit code 2.

### Configuration File (.sdi/config.toml)

Format: TOML. See the Configuration System section for the complete schema and discovery order. Malformed TOML exits with code 2 and a descriptive error message including the file path and line number.

### Boundary Specification (.sdi/boundaries.yaml)

Format: YAML. The boundary spec is the human-ratified architectural intent artifact, read on every snapshot capture for intent divergence detection. It is optional — if absent, SDI operates with inferred boundaries only and skips intent divergence metrics. Absence of a boundary spec is not a degraded mode; it is normal operation for projects that have not yet ratified their boundaries.

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

Key schema elements:

- **modules:** Ratified boundary definitions with file path patterns and layer assignment.
- **layers:** Optional layered architecture constraint with allowed dependency direction (e.g., presentation may depend on domain, but not the reverse).
- **allowed_cross_domain:** Explicitly permitted cross-boundary dependencies with rationale, preventing false positives in boundary violation detection.
- **aspirational_splits:** Planned future boundaries that do not yet exist in code but should be tracked for progress toward separation.

### Previous Snapshots (.sdi/snapshots/*.json)

Format: JSON (SDI's own output format, versioned via the `snapshot_version` field). Previous snapshots are read for seeding the Leiden partition, computing deltas and trends, and drift rate calculation. If no previous snapshots exist, the first snapshot is treated as a baseline with null delta information — null meaning "no previous data," not zero meaning "no change."

### Input Precedence

When multiple sources provide conflicting values, SDI resolves conflicts using a strict precedence order (highest to lowest):

1. CLI flags (`--format json`, `--no-color`, etc.)
2. Environment variables (`SDI_CONFIG_PATH`, `SDI_LOG_LEVEL`, `SDI_WORKERS`, `NO_COLOR`)
3. Project-local config (`.sdi/config.toml` in repository root)
4. Global user config (`~/.config/sdi/config.toml`)
5. Built-in defaults (hardcoded in `sdi/config.py`)

### Malformed Input Handling

| Input Source | Failure | Behavior |
|---|---|---|
| Config TOML | Parse error | Exit code 2 with file path and line number |
| Boundary YAML | Parse error | Exit code 2 with file path and line number |
| Source file | Tree-sitter parse failure | Skip file with warning, continue analysis |
| Source file | No grammar for language | Skip file with warning, continue analysis |
| All source files | No supported languages found | Exit code 3 |
| Previous snapshot | Incompatible schema version | Warn and treat current as baseline (no delta) |
| Git history | Not a git repo | Exit code 2 |

### Stdin

SDI does not read from stdin in v1. All input is file-based. Piping snapshot JSON into `sdi diff` is a future consideration.

### Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `SDI_CONFIG_PATH` | Override config file location | `SDI_CONFIG_PATH=/etc/sdi/config.toml` |
| `SDI_SNAPSHOT_DIR` | Override snapshot storage directory | `SDI_SNAPSHOT_DIR=/tmp/snapshots` |
| `SDI_LOG_LEVEL` | Log verbosity (DEBUG, INFO, WARN, ERROR) | `SDI_LOG_LEVEL=DEBUG` |
| `SDI_WORKERS` | Parallel worker count for file parsing | `SDI_WORKERS=4` |
| `NO_COLOR` | Disable colored output (no-color.org standard) | `NO_COLOR=1` |

## Output Formatting & Modes

### Stdout

SDI supports three output modes, controlled by the `--format` flag:

**Human mode** (default when stdout is a TTY): Colored, formatted tables via the Rich library. Snapshot summaries, diff views with red/green deltas, trend sparklines, boundary maps with indented tree display. Uses unicode box-drawing characters.

**Machine mode** (`--format json`): Structured JSON objects. One JSON document per invocation, no streaming. Designed for piping to `jq` or consumption by CI scripts. All JSON output is valid and self-contained.

**CSV mode** (`--format csv`, available on `sdi trend` only): Headerless CSV for spreadsheet import or consumption by data analysis tools.

### Stderr

All log messages (INFO, WARN, ERROR, DEBUG), progress indicators (tree-sitter parsing progress, graph analysis spinners), and Rich progress bars write exclusively to stderr. This ensures stdout is always clean for piping, even in human mode. A command like `sdi show --format json | jq '.'` always works regardless of log verbosity.

### Files Created

| File | Created By | Purpose | VCS Policy |
|---|---|---|---|
| `.sdi/config.toml` | `sdi init` | Project configuration | Committed |
| `.sdi/boundaries.yaml` | `sdi init`, `sdi boundaries --ratify` | Ratified boundary spec | Committed |
| `.sdi/snapshots/<ts>-<sha>.json` | `sdi snapshot` | Structural fingerprint | Committed |
| `.sdi/cache/partition.json` | `sdi snapshot` | Leiden partition seed | Gitignored |
| `.sdi/cache/parse_cache/` | `sdi snapshot` | Tree-sitter feature cache | Gitignored |
| `.sdi/cache/fingerprints/` | `sdi snapshot` | Pattern fingerprint cache | Gitignored |

### Exit Codes

Exit codes are a public API contract, stable across all versions including pre-1.0:

| Code | Meaning | Commands |
|---|---|---|
| 0 | Success | All |
| 1 | General runtime error or unexpected failure | All |
| 2 | Configuration or environment error | All |
| 3 | Analysis error (e.g., no supported languages) | All |
| 10 | Threshold exceeded | `sdi check` only |

Exit code 10 is reserved exclusively for `sdi check`. No other command may exit with code 10.

### Output Control Flags

| Flag | Scope | Description |
|---|---|---|
| `--format text\|json\|csv` | All commands | Output format (csv only where applicable) |
| `--no-color` | All commands | Disable colored output |
| `--quiet`, `-q` | All commands | Suppress non-essential output |
| `--verbose`, `-v` | All commands | Include additional detail |

### TTY Detection

When stdout is not a TTY, SDI automatically switches to uncolored output and suppresses progress indicators. The `--format` flag still defaults to `text` (not `json`) to avoid surprising users who redirect to a file expecting readable text. The `NO_COLOR` environment variable is respected per the no-color.org convention.

## Configuration System

### Format and Rationale

Configuration uses TOML format at `.sdi/config.toml`. TOML was chosen because it is human-readable, has a clear specification, supports nested tables without YAML's indentation fragility, and is the standard for Python project configuration (`pyproject.toml`). The boundary specification uses YAML in a separate file because boundary specs contain lists-of-objects with comments that carry architectural rationale — YAML's comment support and list syntax are better suited. These are two distinct artifacts with different audiences: config is a developer settings file; boundaries is an architectural intent document.

### Config File Locations

- **Project-local:** `.sdi/config.toml` (in repository root, committed to VCS)
- **Global defaults:** `~/.config/sdi/config.toml` (user-level preferences)

### Discovery Order

1. CLI flags (`--format json`, `--no-color`, etc.)
2. Environment variables (`SDI_*` prefix, `NO_COLOR`)
3. Project-local config (`.sdi/config.toml` in repo root)
4. Global user config (`~/.config/sdi/config.toml`)
5. Built-in defaults (hardcoded in `sdi/config.py`)

All config keys are optional. Missing keys fall through to built-in defaults. Malformed TOML exits with code 2 and a descriptive error including file path and line number.

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

### Per-Category Threshold Overrides

Teams declare migration intent by adding override sections with mandatory expiry dates. An override section without an `expires` field is a configuration error (exit code 2). After the expiry date, the override is silently ignored and default thresholds resume — forcing a conversation if the migration stalled.

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

### Config Management

There is no `sdi config` subcommand in v1. Configuration is edited directly in the TOML file. `sdi init` generates the file with commented defaults. Config changes take effect on the next command invocation — no restart or daemon involved. To reset to defaults, delete `.sdi/config.toml` and run `sdi init` to regenerate, or manually remove specific keys so they fall through to built-in defaults.

## Core Processing Logic

The core pipeline has five stages, executed sequentially on every `sdi snapshot` invocation. Each stage feeds forward — no backward dependencies within a single pipeline run.

```
Source Files → [Stage 1: tree-sitter parsing] → Per-file feature records
    → [Stage 2: Dependency graph construction] → igraph Graph
    → [Stage 3: Leiden community detection] → Cluster assignments + stability
    → [Stage 4: Pattern fingerprinting] → Pattern catalog + entropy
    → [Stage 5: Snapshot assembly + delta] → Snapshot JSON + human summary
```

### Stage 1: Source Parsing (tree-sitter)

The parsing stage walks the repository file tree, filters by `.gitignore` and configured exclude patterns, detects the language per file (extension-based, with tree-sitter grammar probe fallback), and parses each file into a concrete syntax tree (CST) via tree-sitter. From each CST, SDI extracts structural features: imports/dependencies, function/class definitions, exported symbols, and pattern-relevant AST subtrees (e.g., try/catch blocks, API call patterns, data access patterns).

**Output:** Per-file feature records (symbols, imports, pattern instances).

**Complexity:** O(N) in total lines of code. Tree-sitter parsing runs at approximately 1M lines/sec natively; the bottleneck is file I/O.

**Parallelization:** This stage is embarrassingly parallel — each file is independent. SDI uses `concurrent.futures.ProcessPoolExecutor` with a worker count defaulting to `os.cpu_count()`, configurable via `SDI_WORKERS`.

**Memory constraint:** Tree-sitter CSTs are parsed per-file and features extracted immediately. Full CSTs are NOT held in memory simultaneously — parse, extract, discard. Memory usage is proportional to the largest single file, not total codebase size.

**Failure mode:** Missing tree-sitter grammar for a detected language. The files for that language are skipped with a warning on stderr. Analysis continues with available languages. Only if ALL detected languages lack grammars does the command exit with code 3.

### Stage 2: Dependency Graph Construction

SDI builds a directed graph where nodes are files (or modules, configurable) and edges are import/dependency relationships extracted in Stage 1. Cross-language dependency semantics are normalized into a language-agnostic graph: Python imports, JS/TS imports/requires, Go imports, Java imports, and Rust use statements all produce the same edge type. Edges are optionally weighted by import frequency (number of symbols imported) when `weighted_edges = true`.

Graph metrics are computed: node count, edge count, density, connected components, cycle count, hub concentration.

**Output:** igraph `Graph` object + metrics dictionary.

**Complexity:** O(N + E) where N = files, E = import relationships.

**Failure mode:** Cyclic import resolution ambiguity. Handled by recording all edges including cycles — cycles are a measurement target, not an error.

### Stage 3: Community Detection (Leiden Algorithm)

If a previous partition exists (`.sdi/cache/partition.json`), SDI seeds the Leiden algorithm from it. On cold start, the configured `random_seed` (default: 42) ensures reproducibility. The Leiden algorithm runs via leidenalg with the configured `leiden_gamma` resolution parameter.

SDI computes partition stability: the percentage of nodes that kept their cluster membership compared to the previous run. A stability threshold (configurable, default: 3 consecutive runs) debounces boundary updates — a node must appear in a new cluster for N consecutive runs before the boundary map reflects the change.

Additional structural signals computed: dependency directionality between clusters, interface surface area ratio per cluster, change coupling from git history.

**Output:** Cluster assignments, stability score, inter-cluster dependency graph, surface area ratios, change coupling flags.

**Complexity:** Leiden is O(E) per iteration, typically converges in 2–5 iterations. igraph's C implementation keeps this fast even for large graphs.

**Failure mode:** Graph too small for meaningful clustering (< 10 nodes). SDI reports "insufficient structure for boundary detection" and skips boundary metrics.

### Stage 4: Pattern Fingerprinting

SDI ships with seven built-in pattern categories in v1:

| Category | What It Detects |
|---|---|
| `error_handling` | try/catch/except blocks, error propagation patterns, Result/Either types |
| `data_access` | Database queries, ORM calls, repository patterns, raw SQL vs query builder vs ORM |
| `api_validation` | Input validation at API boundaries, schema validation, type checking guards |
| `logging` | Log call patterns, structured vs unstructured logging, log level usage |
| `dependency_injection` | Constructor injection, factory patterns, service locators, global state access |
| `async_patterns` | async/await usage, callback styles, promise chains, concurrency primitives |
| `config_access` | How configuration values are read (env vars, config objects, hardcoded values) |

For each category, SDI queries the AST features from Stage 1 using category-specific tree-sitter queries, computes a structural fingerprint for each pattern instance (a normalized representation of the AST subtree shape — node types and structure, stripped of identifiers and literals), and groups fingerprints by category.

The canonical pattern per category is identified as the most frequent shape (or user-declared in config). Pattern entropy is computed as the count of distinct structural shapes per category.

**Velocity and boundary spread** (computed only when a previous snapshot exists):

- **Per-shape velocity:** The instance count delta for each shape (current count minus previous count). Positive = growing, negative = shrinking, zero = stable. This is a pure integer delta, not a classification.
- **Per-shape boundary spread:** Cross-references each shape's file locations against the boundary partition from Stage 3. Records the count of distinct boundaries each shape spans. This is a pure count, not a judgment.

**Output:** Pattern catalog with per-category shape counts, canonical markers, per-shape velocity, and per-shape boundary spread.

**Complexity:** O(P) where P = total pattern instances. Fingerprint comparison is O(depth) per pair but shapes are hashed for O(1) grouping. Velocity and boundary spread add O(S × B) where S = shapes and B = boundaries, which is negligible.

**Failure mode:** No pattern instances found for a category — report zero entropy, not an error. No previous snapshot for velocity — report velocity as null (baseline snapshot).

### Stage 5: Snapshot Assembly & Delta Computation

SDI combines outputs from Stages 2–4 into a snapshot JSON document. If a previous snapshot exists, deltas are computed for all four SDI dimensions:

| Dimension | What It Measures |
|---|---|
| Pattern entropy delta | Change in distinct shapes per category |
| Convention drift rate | Net new patterns minus consolidated patterns since last snapshot |
| Coupling topology delta | Structural comparison of dependency graphs (cycle count change, hub concentration change, max depth change) |
| Boundary violation velocity | New cross-boundary dependencies since last snapshot, compared against ratified boundary spec if available |

Intent divergence (detected boundaries vs. ratified spec) is computed only if a boundary spec exists. The snapshot is written to the configured directory using atomic file operations.

**Output:** Snapshot JSON file + human-readable summary to stdout.

**Complexity:** O(N + E) for graph comparison, O(C) for pattern catalog diff where C = categories.

**Failure mode:** Previous snapshot has incompatible schema version. SDI warns and treats the current snapshot as a baseline (no delta computed). It never crashes on schema version mismatch.

**Critical invariant:** The first snapshot has null deltas. The delta computation function returns null (not zero) for all dimensions when there is no previous snapshot. Zero means "no change between two snapshots"; null means "no previous data exists."

## Error Handling & Diagnostics

### Error Reporting Strategy

All errors go to stderr. Format: `[LEVEL] message` where LEVEL is ERROR, WARN, or DEBUG. Colors are applied when stderr is a TTY (red for ERROR, yellow for WARN, dim for DEBUG). The Rich library handles formatting.

### Error Categories

**Configuration errors (exit code 2):**
- Missing or malformed `.sdi/config.toml`: includes file path and line number. Example: `Error: invalid config at .sdi/config.toml line 14: expected string value for 'core.languages'`
- Invalid boundary spec YAML: parse error with line number.
- Threshold override missing `expires` field: `Error: [thresholds.overrides.error_handling] requires an 'expires' field`
- Not a git repository: `Error: not a git repository (or any parent). SDI requires git.`
- Git not found: `Error: git not found in PATH`
- Suggestion: `Run 'sdi init' to generate a default configuration`

**Analysis errors (exit code 3):**
- Tree-sitter grammar not available for a detected language: WARN (not fatal). `Warning: no tree-sitter grammar for 'kotlin' — skipping 23 files. Install with: pip install tree-sitter-kotlin`
- All languages unsupported: ERROR + exit 3. `Error: no supported languages found in repository`
- Graph too small for clustering: WARN. Proceeds with partial metrics.

**Runtime errors (exit code 1):**
- Unexpected exceptions are caught at the top level in `cli/__init__.py`. The user sees: `Error: unexpected failure during pattern analysis. Run with SDI_LOG_LEVEL=DEBUG for details.` Full traceback is printed only in DEBUG mode.

**Threshold exceeded (exit code 10, `sdi check` only):**
- One or more SDI dimensions exceeded configured thresholds. Prints which dimensions and by how much. This distinct exit code allows CI scripts to distinguish "drift too high" from "tool broke" without parsing output.

### Verbose and Debug Modes

| Log Level | Output |
|---|---|
| `DEBUG` | Tree-sitter parse timings per file, graph construction details, Leiden iteration count, partition stability details, pattern matching internals, full tracebacks |
| `INFO` (default) | Progress bar during parsing, summary stats after each stage |
| `WARN` | Only warnings and errors |
| `ERROR` | Only errors |

Log level is controlled via `SDI_LOG_LEVEL` environment variable or a `--debug` flag.

## Shell Integration

### Git Hook Integration

Git hooks are the primary integration point for automated SDI usage.

`sdi init` offers to install a **post-merge** git hook that runs `sdi snapshot` automatically on every merge to the configured branch. The hook script is a thin shell wrapper that checks the branch, runs `sdi snapshot --quiet`, and exits 0 always — hook failure never blocks merges.

A **pre-push** hook option runs `sdi check` and exits non-zero to block pushes that would exceed drift thresholds. This is opt-in only. Hook installation is non-destructive: appends to existing hooks or creates new ones.

### CI Integration

`sdi check` with exit codes is the universal CI integration point. Any CI system that can run a command and check exit codes can use SDI:

```bash
pip install sdi
sdi check
```

A polished GitHub Actions marketplace action with PR comments, badge generation, and trend graphs is deferred to post-v1.

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

SDI's JSON and CSV outputs are designed for piping:

```bash
sdi show --format json | jq '.pattern_catalog'
sdi trend --format csv | head -20
sdi diff --format json | jq '.boundary_violations'
```

### Signal Handling

- **SIGINT (Ctrl+C):** Clean shutdown. If mid-snapshot, the incomplete snapshot file is discarded. Atomic writes via tempfile + `os.replace()` ensure partial snapshots never exist on disk.
- **SIGTERM:** Same behavior as SIGINT.
- **SIGHUP:** Not handled (SDI is not a daemon).

### Color Output

SDI respects the `NO_COLOR` environment variable per the no-color.org convention. The `--no-color` flag overrides all other settings. Auto-detection enables color when stderr/stdout is a TTY, plain text when piped. The Rich library handles all color and formatting.

### Progress Indicators

- **File parsing:** Rich progress bar on stderr (`Parsing files [143/892] ...`)
- **Graph analysis:** Spinner on stderr (`Building dependency graph...`)
- **Suppressed** when `--quiet` is set or when stderr is not a TTY.

## File System Operations

### Directory Structure

`sdi init` creates the following directory structure:

```
.sdi/
├── config.toml          # Project configuration (committed to VCS)
├── boundaries.yaml      # Ratified boundary spec (committed to VCS)
├── snapshots/           # Snapshot JSON files (committed to VCS)
│   └── <timestamp>-<short-sha>.json
└── cache/               # Internal caches (gitignored)
    ├── partition.json   # Last Leiden partition for seeding
    ├── parse_cache/     # Tree-sitter parse results keyed by file content hash
    └── fingerprints/    # Pattern fingerprint hashes keyed by file content hash
```

### VCS Policy

Files committed to version control: `.sdi/config.toml`, `.sdi/boundaries.yaml`, `.sdi/snapshots/`. These form the project's structural health record — teams should be able to review snapshot history in git log just like they review code changes.

Files gitignored: `.sdi/cache/`. `sdi init` adds `.sdi/cache/` to `.gitignore` (or creates `.sdi/.gitignore`).

### Atomic Writes

All file creation in the `.sdi/` directory uses `tempfile.NamedTemporaryFile(dir=target_dir, delete=False)` followed by `os.replace(tmpfile, target)` (atomic rename). A crash or SIGINT mid-write never produces a partial snapshot or corrupted config file. This is a non-negotiable system rule.

Snapshot filenames include a timestamp and short SHA, so concurrent runs (unlikely but possible in CI) produce distinct files rather than overwriting each other.

### Temporary Files

Temporary files are created in the target directory (same filesystem, required for atomic rename) via Python's `tempfile` module. They are cleaned up on normal exit and in signal handlers. Stale tempfiles from hard kills have random suffixes and do not interfere with operation.

### Lock Files

None in v1. SDI operations are idempotent — running two snapshots concurrently produces two snapshot files, both valid. The cache directory uses content-addressed filenames (hash-keyed) so concurrent writes do not conflict.

### Snapshot Retention

`sdi snapshot` enforces the configured retention limit (default: 100) synchronously after every write. After writing a new snapshot, if the snapshot count exceeds the limit, the oldest snapshots are deleted immediately before the command returns. Deferred cleanup is not acceptable — the retention limit is a hard guarantee.

### File Permissions

Default umask. No special permission handling — SDI operates within the user's normal permissions context.

## Performance & Resource Usage

### Performance Targets

These are hard constraints for CI viability:

| Project Size | Lines of Code | Files | Target |
|---|---|---|---|
| Small | < 10K | ~100 | < 5 seconds |
| Medium | 10K–100K | ~1,000 | < 30 seconds |
| Large | 100K–500K | ~5,000 | < 2 minutes |
| Very large | 500K+ | 5,000+ | Best-effort, may require exclude patterns |

### Performance Breakdown by Stage (Medium Project)

| Stage | Estimated Time | Bottleneck |
|---|---|---|
| Tree-sitter parsing | 2–5 seconds | File I/O (parsing itself is ~1M lines/sec) |
| Dependency graph construction | < 1 second | In-memory graph building |
| Leiden community detection | < 1s seeded, 2–5s cold start | igraph C backend, 2–5 iterations |
| Pattern fingerprinting | 1–5 seconds | AST query traversal, proportional to pattern count |
| Snapshot assembly + delta | < 1 second | JSON serialization + graph comparison |

### Memory Usage

- **Tree-sitter CSTs:** Parsed per-file; features extracted immediately; CST discarded. Memory proportional to the largest single file, not total codebase size.
- **Dependency graph:** Held entirely in memory via igraph. For 5,000-node graphs, this is negligible (< 50MB). For very large monorepos (50K+ files), this could reach hundreds of MB — documented as a known scaling limit.
- **Pattern fingerprints:** Hash-based, constant memory per pattern instance.

### Caching Strategy

**Parse cache:** Keyed by file content hash (SHA-256 of file bytes). If a file has not changed since the last run, extracted features are reused from `.sdi/cache/parse_cache/`. This makes incremental snapshots (few files changed) near-instant for the parsing stage.

**Partition cache:** The previous Leiden partition is stored in `.sdi/cache/partition.json`. Seeding from it makes subsequent community detection runs faster and more stable.

**Cache invalidation:** Content-addressed (hash-keyed) so stale entries are naturally orphaned. Periodic cleanup on `sdi snapshot` removes orphaned cache entries older than the configured retention window.

### Parallelism

File parsing uses `concurrent.futures.ProcessPoolExecutor`. Worker count defaults to `os.cpu_count()` but is configurable via the `SDI_WORKERS` environment variable (set to 1 for debugging). Graph operations are single-threaded (igraph limitation) but are fast enough that parallelism is unnecessary.

## Versioning & Compatibility

### Versioning Scheme

Semantic versioning (semver): MAJOR.MINOR.PATCH.

### Pre-1.0 (0.x.y)

No stability guarantees. CLI flags, config keys, snapshot schema, and boundary spec format may all change between minor versions. This is explicitly a prototype and validation phase. The snapshot schema will evolve as the team learns what measurements are useful in practice.

### Post-1.0 Stability Guarantees

**CLI interface:** Flags and commands are stable across minor versions. New commands and flags may be added. Existing flags are never removed or have their semantics changed without a major version bump. Deprecation warnings are issued for at least one minor version before removal.

**Snapshot JSON schema:** Versioned via the `snapshot_version` field in every snapshot file. SDI can read snapshots from older schema versions of the same major version for trend computation. Schema changes that would break backward-readable compatibility require a major version bump.

**Config file:** Versioned implicitly. New config keys are additive with defaults — old config files continue to work. Removed keys are silently ignored with a deprecation warning. Config keys are never repurposed (a removed key is reserved forever).

**Boundary spec:** Versioned via the `version` field. Same backward-compatibility rules as the snapshot schema.

**Exit codes:** The semantics of exit codes 0, 1, 2, 3, and 10 are stable across all versions, including pre-1.0. These are a public API contract.

## Distribution & Installation

### Primary Installation Methods

**PyPI (primary):**

```bash
pip install sdi
```

Installs the `sdi` command-line entry point. Pulls tree-sitter and leidenalg as dependencies. Tree-sitter grammar packages are installed separately per-language:

```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
```

Convenience bundles:

```bash
pip install sdi[all]       # All supported grammars
pip install sdi[web]       # Python + TypeScript + JavaScript
pip install sdi[systems]   # Go + Rust + Java
```

**Homebrew:**

```bash
brew tap geoffgodwin/sdi
brew install sdi
```

Formula in a separate `homebrew-sdi` tap repo. Handles Python dependency isolation via Homebrew's Python virtualenv conventions. Includes the most common grammar packages.

**Build from source:**

```bash
git clone https://github.com/GeoffGodwin/sdi.git
cd sdi
pip install -e ".[dev]"
```

Requires Python 3.10+.

### Platform Support

| Platform | Status | Notes |
|---|---|---|
| Linux | Primary | Development and CI platform |
| macOS | Tested in CI | Homebrew formula ensures compatibility |
| Windows | Best-effort | tree-sitter and igraph have Windows wheels; leidenalg may require a C compiler |

### System Requirements

- Python 3.10+ (3.11+ recommended for stdlib `tomllib` support)
- git in PATH (SDI shells out to git for history analysis)
- No other system dependencies — tree-sitter, igraph, and leidenalg all distribute pre-built wheels for major platforms

### Update Mechanism

Manual only in v1: `pip install --upgrade sdi` or `brew upgrade sdi`. No self-update command. A version check on `sdi --version` that prints a notice when a newer version is available on PyPI is a consideration, but since it requires a network call, it would be opt-in only and off by default to respect the "no network calls" philosophy.

## Testing Strategy

### Framework and Tools

- **pytest** for all tests
- **pytest-cov** for coverage reporting (target: 80%+ unit test coverage)
- **pytest-benchmark** for performance benchmarks (not in normal CI, triggered on release tags)
- **ruff** for linting (PEP 8, import sorting)
- **mypy** for type checking (`disallow_untyped_defs = true` for the `sdi/` package)

### Unit Tests (tests/unit/)

Unit tests cover individual functions and classes in isolation, mocking external dependencies (filesystem, git, tree-sitter) where the behavior under test is computation, not I/O:

- **Pattern fingerprinting:** Structurally equivalent AST subtrees produce identical fingerprints; structurally different ones produce different fingerprints. Tested across multiple languages.
- **Dependency graph construction:** Given known import relationships, verify correct graph edges. Each language adapter is tested independently.
- **Snapshot delta computation:** Given two snapshot JSON objects, verify correct computation of all four SDI dimensions.
- **Leiden partition stability:** Seeded partitions are stable when graph changes are small; updates correctly when changes are large.
- **Config loading:** Precedence order, default values, invalid config handling, threshold override validation (missing `expires` rejected).
- **Boundary spec parsing:** YAML parsing, validation of required fields, handling of aspirational splits.

### Integration Tests (tests/integration/)

Integration tests run the full pipeline end-to-end against fixture repos with no mocks — real tree-sitter parsing, real igraph operations, real filesystem interactions:

- **Full pipeline:** Run `sdi snapshot` against fixture repos and verify snapshot output matches expected structure and values.
- **Multi-snapshot workflows:** init → snapshot → modify fixture → snapshot → diff → trend. Verify the full lifecycle produces correct deltas.
- **CLI output:** Snapshot stdout/stderr output for each command and compare against expected output.
- **Git hook integration:** Verify hook installation and that post-merge hook triggers snapshot capture correctly.

### Fixture Repos (tests/fixtures/)

| Fixture | Purpose | Structure |
|---|---|---|
| `simple-python/` | Baseline for most tests. Known imports, one pattern variant, one boundary crossing. | 5–10 Python files |
| `multi-language/` | Cross-language graph construction and adapter integration. | Python + TypeScript (3–5 files each) |
| `high-entropy/` | Pattern fingerprinting accuracy. 4+ error handling styles, 3+ data access patterns. | 10+ Python files |
| `evolving/` | Trend and diff testing. Git repo with 5+ commits introducing progressive drift. | Built by `setup_fixture.py` script |

### Platform Testing

CI matrix: Linux (Ubuntu latest) + macOS (latest), Python 3.10, 3.11, 3.12. Windows is not in the CI matrix for v1 (documented as best-effort).

### Performance Benchmarks (tests/benchmarks/)

pytest-benchmark tests for the parsing stage and Leiden detection on synthetic graphs of increasing size (100, 1,000, 5,000, 10,000 nodes). These track regression across releases, are not run in normal CI, and are triggered manually or on release tags.

### Test Commands

```bash
# Unit tests with coverage
pytest tests/unit/ --cov=sdi --cov-report=term-missing

# Integration tests
pytest tests/integration/

# All tests
pytest

# Benchmarks (manual only)
pytest tests/benchmarks/ --benchmark-only

# Lint
ruff check src/ tests/

# Type check
mypy src/sdi/

# Format check
ruff format --check src/ tests/
```

## Naming Conventions

### Code Naming (Python)

PEP 8 throughout, enforced by ruff in CI:

| Element | Convention | Examples |
|---|---|---|
| Functions, variables, modules | `snake_case` | `compute_entropy`, `parse_cache`, `feature_record` |
| Classes | `PascalCase` | `PatternFingerprint`, `BoundarySpec`, `DivergenceSummary` |
| Module-level constants | `UPPER_SNAKE` | `DEFAULT_GAMMA`, `MAX_RETENTION`, `EXIT_THRESHOLD_EXCEEDED` |

Type hints on all public function signatures. No type hints on local variables unless the type is non-obvious. Docstrings on all public functions and classes (Google style).

### Module Naming

Top-level package: `sdi`. Sub-packages mirror pipeline stages: `sdi.parsing`, `sdi.graph`, `sdi.detection`, `sdi.patterns`, `sdi.snapshot`, `sdi.cli`. Language adapters: `sdi.parsing.python`, `sdi.parsing.typescript`, etc. One class per file is NOT required — group related functionality by module.

### Command and Flag Naming

| Element | Convention | Examples |
|---|---|---|
| Subcommands | Single words | `init`, `snapshot`, `diff`, `trend`, `check`, `show`, `boundaries`, `catalog` |
| Long flags | `--kebab-case` | `--no-color`, `--format`, `--last`, `--output` |
| Short flags | Single letter (common flags only) | `-o` (output), `-f` (format), `-n` (last), `-v` (verbose), `-q` (quiet) |
| Boolean flags | `--flag` / `--no-flag` | `--force`, `--no-color` (Click convention) |
| Environment variables | `SDI_UPPER_SNAKE` | `SDI_CONFIG_PATH`, `SDI_LOG_LEVEL`, `SDI_WORKERS` |

Exception: `NO_COLOR` follows the industry standard (no prefix).

### Domain Term Mapping

| Domain Term | Code Concept | Location |
|---|---|---|
| snapshot | `Snapshot` dataclass | `sdi.snapshot.model` |
| boundary | `BoundarySpec` / `BoundaryModule` | `sdi.detection.boundaries` |
| pattern | `PatternInstance` / `PatternFingerprint` | `sdi.patterns.fingerprint` |
| catalog | `PatternCatalog` (dict: category → fingerprints) | `sdi.patterns.catalog` |
| partition | igraph `VertexClustering` (Leiden output) | `sdi.detection.leiden` |
| divergence | `DivergenceSummary` dataclass (four SDI dimensions) | `sdi.snapshot.model` |
| drift rate | float (delta / interval, always a rate) | `sdi.snapshot.delta` |

## Config Architecture

### Values That Must Live in Config

These values are project-specific or team-specific and cannot be reasonably hardcoded:

- Leiden gamma parameter (teams must tune to their project's graph density)
- Drift rate thresholds for `sdi check` (project-specific acceptable change rates)
- Snapshot retention count (disk space implications)
- Exclude patterns (project-specific ignore rules beyond `.gitignore`)
- Change coupling history depth and minimum frequency (tuning knobs)
- Pattern categories to detect (must be extensible beyond the built-in catalog)
- Per-category threshold overrides with expiry dates (migration intent declarations)
- Random seed (reproducibility across environments)

### Values That Are Hardcoded

These values are tied to the tool's identity or contract and are not user-configurable:

- Snapshot JSON schema version (tied to code version)
- Exit code semantics (0, 1, 2, 3, 10)
- `.sdi/` directory name (convention)
- Tree-sitter query patterns per language (shipped with the tool, not user-editable in v1)
- Built-in pattern category definitions

### Override Hierarchy

From highest to lowest precedence:

1. **CLI flags** (`--format json`, `--no-color`, etc.)
2. **Environment variables** (`SDI_LOG_LEVEL`, `SDI_WORKERS`, `SDI_CONFIG_PATH`, `NO_COLOR`)
3. **Project-local config** (`.sdi/config.toml` in repo root)
4. **Global user config** (`~/.config/sdi/config.toml`)
5. **Built-in defaults** (hardcoded in `sdi/config.py`)

### Reset to Defaults

Delete `.sdi/config.toml` and run `sdi init` to regenerate with commented defaults. Alternatively, remove specific keys from the file — missing keys fall through to built-in defaults automatically.

## Open Design Questions

### OQ1: Weighted vs. Unweighted Edges

Should import frequency (number of symbols imported) affect edge weight in Leiden community detection? Weighted edges might improve cluster quality by distinguishing a single type import from a module that imports 20 symbols, but they might also introduce noise if a utility module is heavily imported everywhere. The default is unweighted. This needs empirical testing across real codebases. The config toggle `weighted_edges` lets users experiment.

**Information needed to resolve:** Benchmark Leiden output quality (measured by boundary stability and human agreement) on 5+ real codebases with weighted vs. unweighted edges.

### OQ2: Resolution Parameter Auto-Tuning

Leiden's gamma parameter controls cluster granularity. The default (1.0) works for many graphs but may produce too few clusters on large codebases or too many on small ones. Should SDI auto-tune gamma based on graph density, or is a static default with manual override sufficient? Auto-tuning adds complexity and reduces reproducibility. Deferring to manual config for v1.

**Information needed to resolve:** Data on what gamma values real projects converge on after manual tuning. If most projects use 0.8–1.2, auto-tuning adds complexity for little benefit.

### OQ3: Pattern Category Extensibility Mechanism

V1 ships with a built-in catalog of pattern categories and tree-sitter queries per language. Users will want to define custom categories. The mechanism is TBD: tree-sitter query files in `.sdi/`? A Python plugin interface? A TOML-based pattern definition DSL?

**Information needed to resolve:** Real user feedback on what categories people want to define and how they prefer to express them.

### OQ4: Multi-Language Dependency Resolution in Monorepos

When a TypeScript frontend imports from a Python backend via an API contract, that cross-language dependency does not appear in import statements. How (or whether) to model these implicit dependencies is an open question. V1 only tracks explicit in-language imports.

**Information needed to resolve:** Survey of common cross-language coupling patterns (REST API contracts, protobuf, GraphQL) and feasibility of inferring them from static analysis.

### OQ5: Snapshot Storage Scaling

At 100 snapshots retained with JSON files of 10–50KB each, storage is trivial. Some teams might want years of history (1,000+ snapshots). Should there be a compact binary format or a SQLite store?

**Information needed to resolve:** Feedback from early adopters on retention needs. If most teams use < 200 snapshots, JSON files with retention limits remain sufficient.

### OQ6: YAML Library Choice

PyYAML is ubiquitous but loses comments on round-trip. ruamel.yaml preserves comments but is a heavier dependency with a more complex API. Since boundary specs carry architectural rationale in comments, comment preservation matters. Leaning ruamel.yaml.

**Information needed to resolve:** Platform compatibility testing for ruamel.yaml on Linux, macOS, and Windows. If it causes install friction, fall back to PyYAML and document that comments are not preserved on programmatic writes.

### OQ7: Generated/Vendored Code Handling

Files in `vendor/` or `generated/` directories are excluded by default, but generated code that lives alongside handwritten code (e.g., protobuf stubs, ORM models) affects the dependency graph and pattern catalog without being authored by humans or agents. A mechanism for tagging files or directories as "generated" is needed so they can be optionally excluded from pattern entropy calculations while still being included in dependency graph construction.

**Information needed to resolve:** Survey of common generated code patterns and where they live relative to handwritten code. Design a tagging mechanism (config-based, file-header-based, or directory-convention-based).

### Resolved Design Decisions

**R1: Drift vs. Evolution — Measure, Don't Classify.** The approach of automatic classification — having SDI infer from pattern velocity vectors and boundary-locality whether a change is a "migration" or "drift" and suppressing alerts accordingly — was explicitly rejected. It violates the measurement-over-opinion principle (classification requires heuristic thresholds that are opinions, not measurements), the human-ratification principle (the tool would be deciding what changes are acceptable), and creates dangerous false negatives in CI gates (an AI agent consistently adopting a new pattern would create a false convergence signal).

The adopted approach: SDI computes and reports per-shape velocity and per-shape boundary spread as raw measurements. Teams declare migration intent via per-category threshold overrides with expiry dates in `config.toml`. This preserves the core contract: SDI measures divergence from declared intent. For boundaries, declared intent is the ratified boundary spec. For patterns, declared intent is the threshold configuration (including any active overrides). The tool never guesses intent.

## What Not to Build Yet

| Feature | Why Deferred | Potential Milestone |
|---|---|---|
| **IDE/editor plugin** | Requires stable API and snapshot schema. Real-time inline boundary violations would be valuable but depend on a frozen schema. | Post-v1.0 |
| **SaaS dashboard / web UI** | SDI is a measurement instrument, not a platform. JSON output can be consumed by Grafana, Datadog, or custom dashboards. A hosted UI is a separate product. | Separate project |
| **Auto-remediation / gardener agent** | SDI detects and measures drift; it never fixes it. A companion tool generating consolidation PRs is a logical follow-on but out of scope for the measurement instrument. | Separate project |
| **GitHub Actions marketplace action** | Document manual CI integration in v1 (`pip install sdi && sdi check`). A polished reusable action with PR comments and badges is post-v1. | Post-v1.0 |
| **Plugin system for custom analyzers** | V1 ships built-in pattern categories only. A plugin interface requires a stable internal API. | Post-v1.0 after user feedback |
| **Cross-language dependency inference** | Detecting implicit dependencies between services requires understanding API contracts, OpenAPI specs, or protobuf definitions — a significant scope expansion. | Post-v1.0 |
| **Historical backfill UX** | `sdi snapshot --commit REF` works for individual commits. Batch backfill across hundreds of commits (parallelism, progress, storage) is not designed. Users can script it with a bash loop. | Post-v1.0 |
| **Standalone binary distribution** | PyInstaller/Nuitka packaging deferred until the dependency tree stabilizes. Tree-sitter grammar loading from bundled binaries has known complexity. | Post-v1.0 |
| **Real-time / watch mode** | A file-watching daemon violates the Unix philosophy constraint and adds significant complexity. CLI invocation on merge events is the intended cadence. | Not planned |
| **Automatic drift-vs-evolution classification** | Explicitly rejected (see Open Design Questions R1). Would require opinionated heuristics and creates false negatives in CI gates. If ever added, it would be opt-in advisory only, never gate-suppression. | Not planned |
| **Stdin input** | `sdi diff` does not read snapshot JSON from stdin in v1. All input is file-based. | Post-v1.0 consideration |
| **`sdi config` subcommand** | No config management command. Edit `.sdi/config.toml` directly. | Not planned for v1 |
