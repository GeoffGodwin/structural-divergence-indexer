# sdi-rust: Scope and Design Deltas vs sdi-py

**Status:** Pre-implementation seed doc. Lives here while we finish bifl-tracker validation against `sdi-py`. When `sdi-rust` work begins, this is the starting point for that repo's `DESIGN.md` and `CLAUDE.md`.

**Date drafted:** 2026-04-25

## Project transition

- **`sdi-py`** = current repo (`structural-divergence-indexer`), reframed as the **POC**. Freezes at the v0.x milestone that completes bifl-tracker validation. Bug-fix-only afterward. No v1 work on the Python side.
- **`sdi-rust`** = new pristine repo, the **MVP**. Library-first with a CLI shell. Starts at `0.1.0` with its own MAJOR.MILESTONE.PATCH counter — does not inherit the v0/v1 era system from sdi-py. Tekhton drives milestones the same way it did for sdi-py.
- **bifl-tracker's role** is the validation harness for v0. It exercises a frontend + backend + database — sufficient coverage of the four SDI dimensions to pressure-test the design before it's cemented in Rust. Gaps found later get fixed in `sdi-rust`'s multi-iteration arc, not retrofitted into `sdi-py`.

## What carries over unchanged from sdi-py

These are language-agnostic and ratified — they become the spine of `sdi-rust`'s DESIGN.md without rework:

- **Core principles**: measurement over opinion, fever chart not thermometer, automated inference + human ratification, safe defaults / zero mandatory config, composable Unix tooling, language-agnostic core with adapters, deterministic and reproducible.
- **Banned anti-patterns**: ML/LLM in pipeline, network calls during analysis, opinions about code quality, automatic alert suppression, interactive TUI/daemon mode.
- **Pipeline shape**: parsing → graph → detection → patterns → snapshot/delta. Five stages, sequential, no backward dependencies.
- **Module boundaries** (KD-style dependency rules). Rename packages to Rust crate conventions (`sdi-core`, `sdi-parsing`, `sdi-graph`, etc.) but keep the dependency direction.
- **Key Design Decisions KD1–KD2, KD4–KD9** carry forward directly. KD3 (ruamel.yaml) is replaced by a Rust YAML choice — see deltas. KD10 (src layout) becomes "Cargo workspace layout."
- **Non-negotiable rules 1–16**, with the wording adjusted where Python-specific (e.g. "tree-sitter CSTs not held in memory simultaneously" still applies but is enforced via Rust ownership rather than convention).
- **Exit-code contract** (0/1/2/3/10) — public API, unchanged.
- **Config precedence order** (CLI > env > project > global > defaults) — unchanged.
- **Default config keys and values** — unchanged. Same TOML schema.
- **Boundary spec format** — unchanged YAML schema; sdi-rust must read existing `.sdi/boundaries.yaml` files produced by sdi-py.

## What changes

### Tech stack

| Concern | sdi-py | sdi-rust |
|---|---|---|
| Language | Python 3.10+ | Rust (MSRV TBD, likely stable latest) |
| Layout | `src/sdi/` package | Cargo workspace: `sdi-core`, `sdi-cli`, language adapter crates, bindings crates |
| AST parsing | `tree-sitter` Python bindings | `tree-sitter` Rust crate (native) |
| Graph | `igraph` (C wrapped) | `petgraph` (likely) or custom CSR — TBD per Leiden needs |
| Community detection | `leidenalg` | **Native Rust port** — see KD11 below |
| CLI framework | `click` | `clap` |
| Terminal output | `rich` | `ratatui` for tables/progress, `owo-colors` or `anstream` for color |
| TOML | `tomllib` / `tomli` | `toml` crate |
| YAML (boundaries) | `ruamel.yaml` (comment-preserving) | `serde_yaml` for read; comment-preserving write deferred (open question) |
| Distribution | PyPI wheel | crates.io + single-binary releases + bindings (PyO3, napi-rs) |

### Distribution and embedding (the actual point)

This is the reason `sdi-rust` exists. sdi-py is a CLI; sdi-rust is a library with a CLI shell.

- **Core crate** (`sdi-core`) exposes the analysis pipeline as a library API. Pure Rust, no I/O concerns beyond what's necessary.
- **CLI crate** (`sdi-cli`) is a thin wrapper around the core, replicating sdi-py's command surface (`init`, `snapshot`, `diff`, `trend`, `check`, `show`, `boundaries`, `catalog`).
- **Bindings crates** (added incrementally, not all at MVP):
  - `sdi-py` (PyO3) — Python bindings, for Python-based agent runtimes
  - `sdi-node` (napi-rs) — Node bindings, for TS/JS agent runtimes
  - `sdi-wasm` (wasm-bindgen) — only if/when there's a real consumer; not MVP
- **Single-binary releases** for Linux/macOS/Windows, removing the `pip install` friction for non-Python shops.

### Determinism guarantees become stronger

sdi-py's determinism rule ("same commit + config + boundaries = same snapshot") survives. sdi-rust upgrades it from a discipline to a near-guarantee:

- No hash-randomization to fight (`HashMap` order is non-deterministic but `BTreeMap` is — code review enforces use of ordered structures wherever output ordering matters).
- RNG is explicit (`rand` with chosen algorithm + seed).
- Floating-point is controllable via `f64` ordering rules; deterministic across platforms with care on FMA.

The non-negotiable rule "same input → same snapshot" gets stronger language: bit-identical JSON output across runs on the same platform, byte-stable across platforms modulo documented float edge cases.

### Memory safety enforcement

sdi-py rule 15 ("tree-sitter CSTs not held in memory simultaneously") is enforced by convention in Python. In Rust it's enforced by ownership — the parsing crate's API consumes the file content and yields a `FeatureRecord`, and the CST is dropped before the function returns. The rule becomes structural rather than aspirational.

### "What not to build yet" — items that move category

Several items on sdi-py's defer list become MVP scope for sdi-rust because they're the reason for the rewrite:

- **Embeddable library API** — was deferred (sdi-py is CLI-only); is now MVP scope.
- **Standalone binary distribution** — was deferred (PyInstaller complexity); is now trivially in-scope (cargo build).
- **GitHub Actions reusable action** — easier with a single binary, but still post-MVP polish.

Items that remain deferred:

- IDE plugin, SaaS dashboard, auto-remediation/gardener, plugin system, cross-language dependency inference, historical backfill UX, real-time watch mode, automatic drift-vs-evolution classification, `sdi config` subcommand. All for the same reasons as sdi-py.

## New Key Design Decisions specific to sdi-rust

### KD11: Native Rust Leiden implementation

`leidenalg` is replaced with a native Rust port of the Leiden algorithm (Traag et al. 2019) implementing the Modularity and CPM quality functions. Targets ~1500–2500 LOC; no FFI to the C++ implementation.

**Verification approach is the spec, not a footnote:**

- Fixture suite: graphs of varying sizes (50, 500, 5000 nodes) parsed from real codebases including bifl-tracker.
- For each fixture, run both `leidenalg` (via sdi-py or a one-off Python harness) and the Rust port with a fixed seed.
- Pass criteria are *partition quality*, not bit-identity: modularity score within 1% of leidenalg's, community count within ±10%, no community larger than 50% of node count for graphs that leidenalg partitions sensibly, and stable output across re-runs with the same seed.
- This regression suite ships in the `sdi-rust` repo and runs in CI.

### KD12: Library-first, CLI-shell

The product is a Rust library. The CLI is a deployment shape, not the canonical interface. Public API stability commitments apply to `sdi-core`'s public interface, not to CLI flags (which are also stable, but for different reasons — exit codes are the harder contract).

### KD13: Snapshot schema clean break

sdi-rust does not read sdi-py snapshot JSON. Schema version starts fresh (`snapshot_version: "1.0"` for sdi-rust, distinct from any sdi-py version). Trend continuity for users migrating from sdi-py is lost — acceptable given user base size. Boundary specs (`.sdi/boundaries.yaml`) and config (`.sdi/config.toml`) are read-compatible: sdi-rust accepts files produced by sdi-py without modification.

### KD14: WASM is post-MVP

WASM bindings are not MVP scope. The valuable property is "one core, multiple bindings" via cargo workspace, not browser execution specifically. WASM lands when a concrete consumer (browser-based demo, edge analysis worker, etc.) exists. Rust-as-library does not require WASM.

## Compatibility matrix

| Artifact | Compatibility | Notes |
|---|---|---|
| `.sdi/config.toml` | **Read-compatible** | sdi-rust accepts sdi-py config files; new sdi-rust-specific keys are additive. |
| `.sdi/boundaries.yaml` | **Read-compatible** | Schema unchanged. Comment preservation on write may regress (open question — see below). |
| `.sdi/snapshots/*.json` | **Clean break** | sdi-rust does not read sdi-py snapshots. New schema version. |
| `.sdi/cache/` | **Clean break** | Internal; no compat concern. |
| Exit codes | **Identical** | Public API contract. |
| CLI flag surface | **Compatible** | Same commands, same primary flags. New flags added as needed. |

## Freeze criteria for sdi-py

sdi-py freezes at the milestone that completes bifl-tracker validation. Concretely:

1. bifl-tracker has been snapshotted across enough of its development history to exercise the four SDI dimensions (pattern entropy across multiple categories, convention drift rate, coupling topology delta, boundary violation velocity).
2. Boundary inference + ratification has been run end-to-end on bifl-tracker.
3. Threshold overrides with expiries have been exercised at least once.
4. Any design issues surfaced are documented in this file (or its successor in the sdi-rust repo) but are not necessarily fixed in sdi-py — they become input to sdi-rust's design.

After freeze: bug-fix-only on sdi-py. No new milestones. Version stays in v0.x range.

## Open questions to resolve before sdi-rust m01

1. **YAML library choice.** `serde_yaml` is the obvious read path. Comment-preserving write is the open question — sdi-py uses `ruamel.yaml` for this. Options: (a) accept comment loss on programmatic write, document it; (b) use a comment-preserving Rust YAML crate (verify maturity); (c) hand-write a minimal YAML emitter that preserves the boundary spec's specific comment patterns. Recommend (a) for MVP, revisit if users complain.
2. **Graph library.** `petgraph` is the default. If Leiden's hot path needs a more cache-friendly representation (CSR), we may roll our own minimal graph type for the detection stage. Decide after the Leiden port spike.
3. **Tree-sitter grammar distribution.** Compile-time linking (each grammar a build dependency) vs. runtime dynamic loading. Compile-time is simpler and matches Rust ecosystem norms; runtime gives smaller binaries when not all grammars are needed. Recommend compile-time for MVP with feature flags per language.
4. **MSRV.** Rust minimum supported version. Recommend "stable latest minus 2" — generous enough for distros, conservative enough to use modern features.
5. **Crate name on crates.io.** Verify `sdi`, `sdi-core`, `sdi-cli` are available before committing. Reserve early.
6. **License.** sdi-py says MIT or Apache 2.0. Pick one (or dual-license) for sdi-rust. Recommend Apache 2.0 for the patent grant; the gardener-LLM use case has corporate adopters in mind.

## Pre-work for sdi-rust m01

Before opening the new repo and writing the first milestone, the following should be done in `sdi-py`:

- [ ] bifl-tracker validation pass complete (per freeze criteria above)
- [ ] Crate names reserved on crates.io (`sdi`, `sdi-core`, `sdi-cli`, `sdi-rust` if available)
- [ ] License decision made
- [ ] Leiden port spike: 1–2 days running the Rust port against one bifl-tracker graph and confirming partition quality vs. `leidenalg`. This is the gating risk; if it fails, the rest of the plan needs re-evaluation.
- [ ] This doc moved into the new repo as the seed for `DESIGN.md`
