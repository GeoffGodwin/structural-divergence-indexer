# Structural Divergence Indexer

SDI is a CLI tool for measuring structural drift in a codebase over time. It captures periodic snapshots of structure, computes deltas, and helps teams answer:

- Is structural divergence accelerating?
- Which dimensions are getting worse?
- What should we fix first to bring drift back down?

## What SDI tracks

SDI computes the **Structural Divergence Index** — a composite metric across four dimensions:

- **Pattern Entropy** — distinct shapes per category (error handling, async, data access, …)
- **Convention Drift Rate** — velocity vectors describing how patterns evolve over time
- **Coupling Topology Delta** — change in dependency graph structure
- **Boundary Violation Velocity** — rate of imports across declared module boundaries

Each dimension is a measurement, not a verdict. SDI never classifies code as "good" or "bad" — it surfaces evidence and lets humans decide.

## Why SDI

- **Deterministic and local.** No network calls during analysis. Same commit + same config = same snapshot.
- **Fast to adopt.** Run one command in a fresh repo and get a baseline.
- **Trend-first.** The primary output is a fever chart, not a thermometer reading.
- **CI and hooks friendly.** Clear exit codes, scriptable JSON output, no daemon.

## Where to start

- [Quick Start](quickstart.md) — install and capture a first snapshot.
- [Concepts](concepts.md) — what each metric means and how they're computed.
- [CLI Reference](cli.md) — every command and flag.
- [Design](design/index.md) — full design documents (v0 scaffold, v1 actionability).
- [CI Integration](ci-integration.md) — wire SDI into your pipeline.
