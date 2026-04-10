# PROJECT_INDEX.md — structural-divergence-indexer

<!-- Last-Scan: 2026-04-10T20:22:13Z -->
<!-- Scan-Commit: 3498ea9 -->
<!-- File-Count: 19 -->
<!-- Total-Lines: 4779 -->
<!-- DOC_QUALITY_SCORE: 20 -->

**Project:** structural-divergence-indexer
**Scanned:** 2026-04-10T20:22:13Z
**Files:** 19 | **Lines:** 4779

## Directory Tree

.
./.claude
./.claude/agents
./.claude/index
./.claude/index/samples
./.claude/logs
./.claude/logs/archive
./.claude/milestones

## File Inventory

| Path | Lines | Size |
|------|------:|------|
| **.claude/** | | |
| .claude/plan_answers.yaml.done | 1178 | huge |

| **./** | | |
| DESIGN.md | 1116 | huge |
| plan_answers.yaml | 1178 | huge |
| CLAUDE.md | 629 | large |

| **.claude/milestones/** | | |
| .claude/milestones/m01-project-skeleton-config-system-and-core-.md | 51 | small |
| .claude/milestones/m08-cli-commands-snapshot-show-diff-trend-ch.md | 58 | small |

| **./** | | |
| plan_questions.yaml | 130 | small |

| **.claude/milestones/** | | |
| .claude/milestones/MANIFEST.cfg | 14 | tiny |
| .claude/milestones/m02-file-discovery-and-tree-sitter-parsing.md | 45 | tiny |
| .claude/milestones/m03-additional-language-adapters.md | 41 | tiny |
| .claude/milestones/m04-dependency-graph-construction-and-metric.md | 39 | tiny |
| .claude/milestones/m05-leiden-community-detection-and-partition.md | 37 | tiny |
| .claude/milestones/m06-pattern-fingerprinting-and-catalog.md | 43 | tiny |
| .claude/milestones/m07-snapshot-assembly-delta-computation-and-.md | 48 | tiny |
| .claude/milestones/m09-boundary-specification-and-intent-diverg.md | 41 | tiny |
| .claude/milestones/m10-caching-and-performance-optimization.md | 35 | tiny |
| .claude/milestones/m11-git-hooks-ci-integration-and-shell-compl.md | 38 | tiny |
| .claude/milestones/m12-integration-tests-polish-and-packaging.md | 40 | tiny |

| **./** | | |
| .gitignore | 18 | tiny |

## Key Dependencies

(no package manifests detected)

## Configuration Files

| Config File | Purpose |
|-------------|---------|
| .gitignore | Git ignore rules |

## Test Infrastructure

**Test files:** 0

## Sampled File Content

### DESIGN.md

```md
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
... (1046 lines omitted)
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
```
