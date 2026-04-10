# PROJECT_INDEX.md — structural-divergence-indexer

<!-- Last-Scan: 2026-04-10T13:47:06Z -->
<!-- Scan-Commit: b7f3b01 -->
<!-- File-Count: 22 -->
<!-- Total-Lines: 10259 -->
<!-- DOC_QUALITY_SCORE: 20 -->

**Project:** structural-divergence-indexer
**Scanned:** 2026-04-10T13:47:06Z
**Files:** 22 | **Lines:** 10259

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
| **.claude/logs/** | | |
| .claude/logs/20260410_084201_plan-interview.log | 2386 | huge |
| .claude/logs/20260410_084845_plan-generate.log | 2812 | huge |

| **.claude/** | | |
| .claude/plan_answers.yaml.done | 1178 | huge |

| **./** | | |
| DESIGN.md | 1174 | huge |
| plan_answers.yaml | 1178 | huge |
| CLAUDE.md | 609 | large |

| **.claude/milestones/** | | |
| .claude/milestones/m01-project-skeleton-and-core-infrastructure.md | 64 | small |
| .claude/milestones/m02-source-parsing-and-file-discovery.md | 60 | small |
| .claude/milestones/m03-dependency-graph-construction.md | 55 | small |
| .claude/milestones/m04-community-detection-and-boundary-managem.md | 66 | small |
| .claude/milestones/m05-pattern-fingerprinting-and-catalog.md | 67 | small |
| .claude/milestones/m06-snapshot-assembly-delta-and-core-command.md | 102 | small |
| .claude/milestones/m07-multi-language-adapter-support.md | 65 | small |
| .claude/milestones/m08-ci-gate-sdi-check-and-git-hook-integrati.md | 72 | small |
| .claude/milestones/m09-cli-polish-and-output-formatting.md | 63 | small |
| .claude/milestones/m10-performance-optimization-and-caching.md | 58 | small |

| **./** | | |
| plan_questions.yaml | 130 | small |

| **.claude/index/** | | |
| .claude/index/inv_Xe7sRM4K | 0 | tiny |
| .claude/index/tree.txt | 8 | tiny |

| **.claude/milestones/** | | |
| .claude/milestones/MANIFEST.cfg | 14 | tiny |
| .claude/milestones/m11-testing-fixtures-and-quality-gate.md | 49 | tiny |
| .claude/milestones/m12-packaging-distribution-and-documentation.md | 49 | tiny |

## Key Dependencies

(no package manifests detected)

## Configuration Files

| Config File | Purpose |
|-------------|---------|

## Test Infrastructure

**Test files:** 0

## Sampled File Content

### DESIGN.md

```md
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
... (1104 lines omitted)

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
```
