# SDI v1 — Design Document

**Status:** Draft. Forward-looking design seeding the next wave of milestones.
**Scope:** The `sdi` CLI only. Companion surfaces (dashboards, agents, remediation bots) are reserved for v2.
**Supersedes:** Nothing. This document *extends* `.tekhton/DESIGN.md` (v0) — it does not replace it. Where this document is silent, v0 governs.
**Audience:** Maintainers, milestone authors (Tekhton), and early adopters evaluating whether SDI is on a trajectory they can build on.

---

## 0. Thesis: Measure → Prove → Act

SDI's lifecycle is three versions, each with a sharply different promise to the user:

| Version | Promise | Status |
|---|---|---|
| **v0** | "We *can* measure structural drift, reproducibly, across languages, without opinion." | Shipped (M1–M14). |
| **v1** | "The measurements are *meaningful*, and you can act against them." | This document. |
| **v2** | "SDI *acts* — companion surfaces (dashboard, gardener) close the loop." | Seeded at §10. |

v0 established the instrument. A user can run `sdi snapshot` on any supported codebase and get a reproducible fingerprint of its structural state — pattern entropy, Leiden-inferred boundaries, convention velocity vectors, boundary violation counts. The metrics are defensible: every number decomposes into traceable inputs, no ML/LLM in the pipeline, determinism guaranteed by seed. That was the v0 contract, and it is met.

v0 has a known gap the users will feel the moment they start using SDI in earnest: **the numbers are real, but the path from "a number moved" to "here is what to do about it" is too long**. `sdi diff` tells you error_handling entropy went from 4 to 7. It does not tell you *which three new shapes appeared*, *where*, *who introduced them*, or *whether one of them is likely a deliberate migration versus incidental drift*. A tech lead reading a v0 snapshot has to do the detective work themselves. This is fine for the early-adopter phase, where the measurement itself is the novelty. It is not fine once the tool graduates to "we gate merges on this."

v1's job is to shorten that path without betraying v0's principles. The metric surface stays the same; what changes is what SDI is willing to *say about* a metric movement — always as measurement or attribution, never as classification or judgment. When pattern entropy rises, v1 tells you *which fingerprints* are new, *which files* contain them, *which commits* introduced them, and *which existing shapes* are structurally closest. It does not tell you whether that was good or bad. The user still decides.

v1 also hardens v0. Several v0 decisions were shipped with "collect data, revisit" attached (OQ1–OQ7 in v0's DESIGN.md). v1 is the revisit. One v0 hardening item is load-bearing for real-world use and cannot wait: the cycle-detection performance cap (`.tekhton/HUMAN_ACTION_REQUIRED.md`). Phase 0 below addresses it before any new capability lands.

v2 is out of scope for this document — but v1's decisions constrain what v2 can look like, so §10 ("What Not to Build Yet — seeds v2") names the things v1 must *not* attempt, so v2 has clean ground to build on.

---

## 1. Principles Carried Forward From v0

These remain in force. They are summarized here, not restated — v0's `.tekhton/DESIGN.md` is the authoritative text.

- **Measurement over opinion.** Every number decomposes to traceable inputs. No heuristic that cannot be explained in code. (v0 §"Core Principles")
- **Fever chart, not thermometer.** Trend and rate of change are the primary output; absolute state is supporting context. (v0 §"Core Principles")
- **Automated inference, human ratification.** SDI proposes; a human ratifies `.sdi/boundaries.yaml`. The tool measures divergence from *declared* intent. (v0 §"Core Principles", KD1)
- **Safe defaults, zero mandatory config.** `sdi snapshot` on an un-initialized repo must produce useful output. (v0 §"Core Principles")
- **Composable Unix tooling.** Local filesystem + git only. Stdout = data, stderr = logs. Exit codes are a public API. (v0 §"Non-Negotiable Rules" #8, #9)
- **Language-agnostic core, language-specific adapters.** Tree-sitter provides consistent AST representation; adapters are thin. (v0 §"Core Principles")
- **Deterministic and reproducible.** Same commit + same config + same boundaries = same snapshot. Seeded Leiden, no network, no LLM. (v0 §"Non-Negotiable Rules" #1–#3)
- **Never classifies code as good or bad.** Pattern entropy is a measurement, not a verdict. Threshold breaches are "exceeded," never "violations." (v0 §"Non-Negotiable Rules" #4, KD1)
- **Alert suppression is always time-boxed.** Threshold overrides *must* have `expires` dates. (v0 §"Non-Negotiable Rules" #5, #6)

The banned anti-patterns from v0 also stand: no ML/LLM in pipeline, no network calls, no opinions about code quality, no automatic alert suppression, no interactive TUI or daemon mode.

## 2. New Principles for v1

These are additions, not replacements. They exist because v1's scope (actionability, extensibility) creates new failure modes v0 did not have to worry about.

### P1. Actionability must be traceable

v1 adds "where to look" and "what changed" surfaces — hotspot rankings, attribution to files/commits/authors, nearest-neighbor lookups across pattern shapes. Every such surface must decompose to the same inputs that produced the headline metric. If `sdi diff` says "three new error-handling shapes appeared," the user must be able to ask "which ones, where, and in which commits" and get an answer grounded in the same snapshot data. No additional inference layer, no heuristic re-ranking.

**Concretely:** Every attribution field in a snapshot or diff JSON is either (a) directly computed from the same AST/graph/git inputs that produced the fingerprint, or (b) absent. There is no "confidence score" field. There is no "suggested cause" field.

### P2. No classification creep

v1 will be under pressure to classify. Users will ask "is this drift or a migration?" — and v1 *could* answer, by correlating threshold-override declarations with velocity vectors, or by using co-change frequency to guess intent. v1 does not take that bet. Classification remains the user's job; SDI's job is to surface the evidence well enough that the user can decide in under a minute.

**Concretely:** `sdi diff`, `sdi trend`, and `sdi check` never emit verdicts. They emit measurements, attributions, and neighbor lookups. A category marked with an active `[thresholds.overrides.*]` is reported as "exceeded (override active, expires YYYY-MM-DD)", never as "migration in progress." The override is a user declaration of intent; SDI reports that declaration, it does not validate it.

### P3. Extensibility must preserve determinism

v1 introduces extensibility for pattern categories (resolving v0 KD6) and likely for language adapters. Both are attack surfaces against v0's determinism guarantee. A plugin that calls out to the network, imports a model, reads wall-clock time, or produces non-reproducible output corrupts SDI's core promise.

**Concretely:** The plugin contract is a pure function from AST (or a subset) to a deterministic data structure. Plugins are loaded from explicit, in-repo paths — never from a remote registry during analysis. Plugin discovery emits a manifest (plugin name, version, content hash) into every snapshot, so a snapshot is reproducible iff the same plugin set is installed. Plugins that fail to load are a config error (exit 2), not silently skipped.

### P4. Advisory surfaces are labeled advisory and never gate

v1 adds surfaces the user might mistake for prescriptions: `sdi explain <shape>`, canonical-pattern proximity, hotspot rankings, remediation hints. These are advisory. They inform; they do not gate. Only `sdi check` gates, and it gates on the same threshold logic as v0 — no advisory surface contributes to the check verdict.

**Concretely:** Advisory output fields are namespaced (`hints.*`, `neighbors.*`, `explanations.*`) and explicitly documented as non-gating. `sdi check` reads only threshold data, never advisory fields. This keeps CI-gating logic trivially auditable and keeps advisory surfaces free to evolve without destabilizing gate behavior.

### P5. Performance budgets are a shipped contract, not a best effort

v0 documented performance targets; v1 treats them as a contract enforceable via `tests/benchmarks/` and release-time regression gates. An actionability feature that ships with a 3× slowdown on the baseline pipeline is a regression, not a feature. Every v1 phase lists its budget impact explicitly.

**Concretely:** The v0 baseline (cold parse + full pipeline) is the reference. Each v1 addition declares a ceiling cost (percentage or absolute). Benchmarks in CI reject PRs that breach the declared ceiling without an accompanying budget update reviewed by a maintainer.

---

## 3. Phase 0 — v0 Hardening

Phase 0 is preconditions. Nothing in Phases A–D ships before Phase 0 lands, because these are the items that will bite hardest once adoption grows beyond early users who tolerate rough edges.

### 3.1 Cycle detection cost cap (HUMAN_ACTION_REQUIRED)

**Problem.** `sdi/graph/metrics.py:126` calls `graph.simple_cycles()`. Its worst case is exponential in the cycle count; a dense or adversarial import graph can push a single `sdi snapshot` into multi-minute or multi-gigabyte territory. This is a latent denial-of-service against SDI itself on real codebases.

**Resolution.**
- Add `[graph] cycle_detection` config section with:
  - `enabled = true` (default)
  - `max_cycles = 1024` (hard cap; stop enumeration at this count)
  - `time_budget_ms = 2000` (wall-clock cutoff on the `simple_cycles()` call)
- When either cap trips, record `graph.cycles_truncated = true` and `graph.cycles_budget_exceeded = "max_cycles" | "time_budget"` in the snapshot. The recorded cycle count is the count observed *before* the cap was hit, not zero.
- `sdi show` and `sdi diff` surface a one-line `⚠ cycle detection truncated at cap` when this flag is set, so users know the number is a lower bound.
- Benchmark fixture: a synthetic graph with ≥10k cycles that exercises the cap. Benchmark must complete within 3× `time_budget_ms`.
- Exit cleanly on cap — never crash, never OOM. Cap hits are normal operation.

**Budget impact.** Neutral or positive. The cap reduces worst-case time; the typical case is unchanged.

**Non-negotiable rule added:** Cycle enumeration is always capped. An uncapped call path is a regression.

### 3.2 Resolution of v0 Open Questions (OQ1–OQ7)

v0 shipped with seven questions marked "collect data, revisit." v1 is the revisit. Each resolution below is a *framework for deciding* — the actual decision lands in a v1 milestone, informed by telemetry from adopters. This section fixes the framework so the decisions are auditable.

**OQ1 — Leiden gamma default and auto-tuning.**
- Resolution: Keep gamma 1.0 as default. Ship `sdi boundaries --suggest-gamma` as an advisory surface that reports modularity at a grid of gamma values (0.5, 0.75, 1.0, 1.25, 1.5, 2.0). Never auto-apply.
- Rationale: Auto-tuning in the analysis pipeline violates determinism (tuning run → chosen gamma → second run). Advisory report preserves reproducibility.
- Closed by: v1 milestone "Leiden resolution advisory."

**OQ2 — Weighted vs unweighted edges.**
- Resolution: Keep unweighted default. Collect telemetry from early adopters who flip `weighted_edges = true` and compare partition stability. Decide on default for v1.x minor release, not v1.0.
- Rationale: Flipping the default changes every existing adopter's snapshot shape. That requires data, not intuition.
- Closed by: v1.x minor, not gated on any v1 milestone.

**OQ3 — Custom pattern category mechanism.**
- Resolution: Tree-sitter query files in `.sdi/categories/*.scm` plus a TOML manifest per category. No Python plugin API in v1.
- Rationale: Tree-sitter queries are declarative, sandboxed, and deterministic by construction. A Python plugin API would create an unbounded determinism surface (see P3).
- Closed by: Phase C milestone "Pattern category plugin system."

**OQ4 — Cross-language dependency detection.**
- Resolution: Scoped-in via *contract file* parsing only (OpenAPI, protobuf, GraphQL SDL). No code-level cross-language resolution. Contract files produce synthetic "contract nodes" in the graph; callers in any language reference them by stable id.
- Rationale: Contract-file parsing is deterministic and cheap. Code-level cross-language resolution (TypeScript `fetch('/api/users')` → Python `@router.get('/users')`) requires inference SDI has no business doing.
- Closed by: Phase C milestone "Cross-language contract inference."

**OQ5 — Generated/vendored code tagging.**
- Resolution: Explicit tagging via `.sdi/generated.txt` (gitignore-style globs), plus auto-detection heuristics for well-known markers (`# DO NOT EDIT`, `// Code generated by`, `@generated`). Auto-detected files are reported in `sdi show --generated` so users can promote heuristic matches into the explicit list.
- Rationale: Generated code dominates pattern entropy if not excluded, but auto-classification is dangerous (false positives exclude real code from metrics). Dual mechanism: explicit is authoritative, auto-detection is advisory.
- Closed by: Phase A milestone "Generated code tagging."

**OQ6 — ruamel.yaml vs PyYAML.**
- Resolution: Stay on ruamel.yaml. Document Windows install notes in README. Revisit only if install-friction bug reports cross a threshold.
- Rationale: Comment preservation in `.sdi/boundaries.yaml` is load-bearing — the rationale comments *are* the architectural record. Dropping to PyYAML silently loses that.
- Closed by: Status quo; no milestone needed.

**OQ7 — Snapshot schema freeze.**
- Resolution: v1.0 ships snapshot schema version `2`. Schema `1` (v0) snapshots are readable for trend/diff for the lifetime of v1.x. Schema changes within v1.x are additive-only (new fields, never renamed or removed). Non-additive changes require schema `3` and a major version bump.
- Rationale: Trend data is the product. A schema migration that loses history destroys the product. Additive-only is the only sustainable posture.
- Closed by: Phase 0 milestone "Snapshot schema v1 freeze."

### 3.3 Snapshot schema v1 freeze criteria

Before any Phase A/B/C/D field lands in a snapshot, schema v1 must be frozen. The freeze criteria:

1. **Every v0 field retained with identical semantics.** v1 readers accept v0 snapshots; v0 readers that encounter v1 snapshots see the `snapshot_version` mismatch and treat as baseline (per v0 non-negotiable #13).
2. **New fields are optional.** Missing-field handling defaults to "not computed," not "zero."
3. **Namespaced extension points reserved.** Top-level keys `hints`, `neighbors`, `explanations`, `attributions`, `plugins` are reserved in the v1 schema even if not populated in v1.0. This prevents naming collisions as phases land.
4. **Null semantics preserved.** `null` = "no previous data" (first snapshot, missing input); `0` or `[]` = "computed, empty result." v1 code must preserve this distinction in every new field.
5. **Schema document published.** `docs/snapshot-schema-v1.md` ships with v1.0 and is the authoritative reference; a JSON Schema file (`docs/snapshot-schema-v1.json`) is generated from it and used in tests.

### 3.4 Module boundary hygiene

v0's module boundaries (`cli/ → *`, `parsing/ → tree-sitter only`, `patterns/ → parsing only`, `snapshot/ = assembly point`) held well through M1–M14 but have frayed in two places per DRIFT_LOG:

- CLI commands duplicate path-bounds logic. Resolve by introducing `sdi.cli._path_bounds` (single helper) and migrating all six commands that accept path scopes to use it.
- `sdi.config` is drifting toward carrying runtime state (caching loaded TOML across calls in the same process). Resolve by making config loading pure-functional: `load_config(paths) → Config` with no module-level cache. Any caching happens in the caller.

Both are pure refactors with tests; they belong in Phase 0 because every later phase touches CLI path handling or config.

### 3.5 Phase 0 acceptance

Phase 0 is done when:

- Cycle detection cap shipped with benchmark fixture and snapshot flag.
- OQ6 documented (status quo). OQ1, OQ3, OQ4, OQ5, OQ7 have milestone entries. OQ2 has a telemetry plan.
- Snapshot schema v1 document and JSON Schema file ship. v0 snapshot fixtures round-trip through v1 readers in integration tests.
- `sdi.cli._path_bounds` in use across all six commands; no inline path-bounds logic remains.
- `sdi.config` has no module-level state; tested via two successive `load_config()` calls with different env var states returning different results.

No Phase A/B/C/D work ships before Phase 0 is complete.

---

## 4. Phase A — Measurement Depth

Phase A completes what v0 started: the measurement surface. v0 shipped with known gaps (shell support landing only in M13–M14, seven pattern categories, no generated-code handling). Phase A closes them. No new user-facing verbs land here — the CLI surface is unchanged; what changes is what v0's existing commands *see*.

### 4.1 Language breadth completion

**v0 state.** Python, JavaScript, TypeScript, Go, Java, Rust via dedicated adapters. Shell lands in M13–M14 (planned).

**Phase A delta.**
- Finish M13–M14 rollout: shell adapter ships in the default grammar set, not an opt-in extra.
- Add **C/C++** and **Ruby** adapters. Both have stable tree-sitter grammars and meaningful import semantics (`#include`, `require`/`require_relative`). C/C++ is specifically called out because a measurable fraction of infra codebases still carry C extensions even when the primary language is Python or Ruby.
- Add **Kotlin** adapter. Kotlin's growth in backend/Android makes it the highest-signal omission after C/Ruby.
- Refuse scope-creep into less-common languages (Scala, Elixir, Zig, OCaml, Swift, Dart) until adopter telemetry demonstrates demand. Each new adapter costs ongoing maintenance; we add them on evidence.

**Adapter contract additions.** Every adapter now reports:
- `adapter_version` (independent semver per adapter, shipped in snapshot under `plugins.adapters.<lang>`)
- `grammar_version` (tree-sitter grammar package version at parse time)
- `skipped_files` with reason codes: `parse_error`, `grammar_version_mismatch`, `encoding_error`, `size_exceeded`

These fields belong to the v1 schema freeze (§3.3) — they must be reserved before any adapter ships them.

**Budget impact.** Per-adapter cost is bounded by file count in that language. No pipeline-wide ceiling change; adapters that a project doesn't use don't execute.

### 4.2 Pattern category expansion

**v0 state.** Seven built-in categories: `error_handling`, `data_access`, `logging`, `async_patterns`, `class_hierarchy`, `context_managers`, `comprehensions`. Shell expands `error_handling`, `async_patterns`, `data_access`, `logging` in M14.

**Phase A delta.** Add four more built-in categories. Each is a structural shape with a clear tree-sitter query and no ambiguity with existing categories:

1. **`configuration_loading`** — How modules read config (env vars, TOML/YAML/JSON parsing, framework-specific config objects). High drift here correlates with boundary ambiguity between infra and domain.
2. **`dependency_injection`** — Constructor injection, decorator-based DI, service-locator patterns, manual wiring. Drift here predicts coupling-topology delta.
3. **`serialization`** — `to_json`/`from_json`, dataclass/pydantic/attrs boundaries, manual dict packing. A strong signal for API-surface stability.
4. **`testing_patterns`** — Fixture style, mocking approach, parametrization vs. repetition. Kept distinct from production categories so test drift doesn't pollute production metrics; `sdi show --tests-only` exposes it.

Categories 1–3 apply to every supported language; category 4 is language-specific and reports only when the project has a detected test directory.

**Custom categories** (resolves OQ3): deferred to Phase C. Phase A ships built-ins only.

**Budget impact.** Each category is an additional tree-sitter query pass per file. Measured per-category overhead from v0 is ≈2–4% of parse time. Four new categories project to ≤16% parse-time increase. Phase A declares a ceiling of **+20% cold parse time** for the combined category expansion; anything over that requires category-level query optimization before ship.

### 4.3 Measurement accuracy improvements

Three v0 measurements have known weaknesses that Phase A addresses:

**Pattern fingerprint collision.** v0 structural hashes collide on superficially different shapes in some adapters (notably shell's `_shell_structural_hash` folding `command_name`, which was a deliberate trade-off for M13). Phase A adds a *fingerprint tier* field: `tier = "structural" | "named"` where `named` includes salient identifiers (function names, keyword-argument names) and `structural` is v0's existing behavior. Both are computed; snapshots carry both. Consumers pick the tier they want. Default reports stay on `structural` for backward compatibility.

**Leiden partition drift on small codebases.** Under ~200 nodes, Leiden partitions are unstable across runs even with seeded start. Phase A adds a `partition.stability_score` field reporting inter-run agreement across 3 re-runs at cold start. Low score is surfaced in `sdi show` as an advisory. No behavior change — the partition is still used — but users see the warning instead of chasing spurious boundary changes.

**Coupling metric sensitivity.** v0 reports coupling topology delta as a single scalar. It's too compressed. Phase A decomposes it into `coupling.inter_module_edges`, `coupling.intra_module_edges`, `coupling.bridge_nodes`, `coupling.articulation_points`, and reports all four in the snapshot. The single scalar is still computed (backward compatible); the decomposition is new.

All three are additive and preserve v0 semantics.

### 4.4 Generated code tagging (resolves OQ5)

`.sdi/generated.txt` ships as a gitignore-style explicit list. Auto-detection runs on every parse and populates `snapshot.generated.auto_detected` with files matched by known markers:

- `# DO NOT EDIT` (any case, any prefix comment style)
- `# Code generated by` / `// Code generated by`
- `@generated`
- Well-known directory markers: `*_pb2.py`, `*.pb.go`, `*_generated.go`, `*/__generated__/*`

Auto-detected files are **not** excluded from metrics by default. They are tagged. Users promote a file to "always excluded" by adding it to `.sdi/generated.txt` explicitly. This preserves v0's safe-default (we never silently exclude code), while making the promotion a one-liner.

`sdi show --generated` lists auto-detected and explicit entries side by side. `sdi check` treats explicit-list files as non-contributing to entropy; auto-detected files still count toward entropy unless promoted. This is the v1 answer to the "is this code really generated?" problem: let the user decide, but make deciding cheap.

### 4.5 Phase A acceptance

Phase A is done when:

- C/C++, Ruby, Kotlin adapters ship with the contract additions in §4.1.
- Four new pattern categories (configuration_loading, dependency_injection, serialization, testing_patterns) ship as built-ins and pass the +20% cold-parse ceiling benchmark.
- Fingerprint `tier` field populates in every snapshot; `partition.stability_score` populates for graphs under 200 nodes.
- Coupling decomposition present in every snapshot.
- `.sdi/generated.txt` + auto-detection + `sdi show --generated` all functional. Integration test verifies auto-detected Python + Go protobuf stubs.
- All v0 integration tests still pass with Phase A schema additions.

---

## 5. Phase B — Actionability

Phase B is the heart of v1. Phases 0 and A built the foundation; Phase B is the reason v1 exists. Every surface here answers "what do I do with this number?" — and answers it without classifying, judging, or suppressing.

### 5.1 Hotspot ranking in `sdi diff`

**v0 state.** `sdi diff <old> <new>` reports per-dimension deltas. It does not rank *where* the delta concentrated.

**Phase B delta.** `sdi diff` gains a hotspot section in both text and JSON output. Hotspots are ranked by absolute contribution to the delta, not by verdict:

```
Hotspots (pattern_entropy, top 5 files by contribution):
  src/billing/invoice.py       +3 new shapes   (2 error_handling, 1 data_access)
  src/billing/tax.py           +2 new shapes   (2 error_handling)
  src/users/profile.py         +1 new shape    (1 error_handling)
  src/notifications/email.py   -2 removed      (2 error_handling; canonical shape retained)
  src/api/v1/webhooks.py       +1 new shape    (1 async_patterns)
```

Ranking is pure accounting: sum of `|Δshape_count|` per file per category. No weighting by file size, author, or recency — those would be heuristics. The JSON form carries the raw contribution per file per category so downstream tools can apply their own weighting.

`--top N` flag to control ranking depth. Default 10. `--hotspots-only` suppresses the per-dimension summary.

### 5.2 Where-to-look attribution

For each hotspot line, `sdi diff --attribute` additionally resolves:
- **File path + line range** of the new/removed/modified shapes (from the fingerprint's source location).
- **Git blame** for those line ranges at the target snapshot's commit. Each shape gets `introduced_in_commit`, `introduced_by_author`, `introduced_at_timestamp`.
- **Neighbor shapes:** the top 3 existing shapes (by fingerprint Hamming distance) in the same category, with their file paths. This answers "is this new shape close to an existing canonical one?"

Attribution is opt-in (`--attribute` flag) because it requires `git blame` which is slower. It reuses the existing blame infrastructure from `sdi snapshot --commit`, not new git logic.

**Strict rule (reinforcing P2):** Attribution fields are raw git metadata. SDI does not interpret them. "Author X introduced this" is never coupled to a verdict. The user reads the attribution and decides.

### 5.3 `sdi explain <shape_id>`

New verb. Takes a fingerprint id (from a snapshot's pattern catalog) and reports:

- The shape's category, structural and named fingerprint values, first-seen snapshot, last-seen snapshot.
- Every file + line range instance in the latest snapshot.
- Nearest 5 neighbor shapes in the same category (Hamming distance on fingerprint bits).
- If a canonical shape exists for the category (§5.5), distance to canonical.
- Git history of the shape's appearance count across the snapshot retention window (ASCII sparkline in text mode; array in JSON).

`sdi explain` is the tool a tech lead reaches for when `sdi diff` flags a new shape and they want to know "has this ever appeared before? where does it live now? what's close to it?" before deciding whether to consolidate, canonize, or leave alone.

`sdi explain` is read-only and advisory. It never gates. It is not consulted by `sdi check`.

### 5.4 Remediation hints (pure advisory)

`sdi diff --hints` and `sdi show --hints` emit a `hints` array per hotspot. Hints are entirely derivable from snapshot data — they are phrasings of facts the user could compute themselves, not recommendations:

- *"5 shapes in `error_handling` have appeared in the last 3 snapshots; the top shape by instance count is `fp_a1b2c3`. `sdi explain fp_a1b2c3` for detail."*
- *"Module `billing` has 3 shapes in `data_access` that do not appear in any other module; they may be local conventions worth canonizing."*
- *"Category `async_patterns` has entropy trending down over 5 snapshots; the retained canonical shape is `fp_f00ba7`."*

Hints are rule-based, not learned. The rules live in `src/sdi/hints/rules.py` and are unit-tested. Every hint cites the specific snapshot fields that produced it, so users can audit. Hints are skipped (not emitted empty) when their triggering condition doesn't hold.

**P4 enforcement:** `sdi check` does not read `hints`. Hints have no effect on exit code.

### 5.5 Canonical pattern pinning

**v0 state.** Every pattern shape is equal. There is no concept of "the preferred error-handling shape for this repo."

**Phase B delta.** Users can pin a canonical shape per category in `.sdi/canonicals.yaml`:

```yaml
sdi_canonicals:
  version: "1.0.0"
  pinned:
    - category: "error_handling"
      fingerprint: "fp_a1b2c3d4"
      pinned_at: "2026-05-01"
      pinned_by: "geoffgodwin"
      reason: "Chosen per ADR-0051: Result-type error propagation"
    - category: "logging"
      fingerprint: "fp_9e8f7a6b"
      pinned_at: "2026-05-01"
      pinned_by: "tchen"
      reason: "Structured logging with trace context per ADR-0048"
```

A pinned canonical surfaces in:
- `sdi show --canonicals` lists them.
- `sdi diff` reports distance-to-canonical for new shapes in pinned categories (e.g., *"new shape fp_xyz has Hamming distance 14 from canonical fp_a1b2c3d4 (mean category distance: 8)"*).
- `sdi explain` shows distance-to-canonical.

Pinning is **not** enforcement. A non-canonical shape still counts toward entropy. SDI does not reject PRs that introduce non-canonical shapes. Pinning is *orientation*: it gives users a reference point for "how far has this new shape drifted from what we said we wanted?" The human still reads the number and decides.

A canonical entry stops affecting output if its fingerprint no longer appears in any snapshot in the retention window. `sdi show --canonicals` flags stale entries with `status: stale, last_seen: <snapshot_ref>`.

Per-category canonicals are capped at one per category. Multiple canonicals per category is a config error (exit 2). This is deliberate: "pick one" is part of the value.

### 5.6 Aspirational split progress activation

**v0 state.** `.sdi/boundaries.yaml` supports `aspirational_splits` with a `target_date`, but the data is inert — nothing reports on progress.

**Phase B delta.** Every snapshot now computes, per aspirational split:
- Count of inter-cluster edges between the intended sub-boundaries.
- Count of pattern shapes unique to each intended sub-boundary.
- A scalar `progress_score` in [0, 1] derived purely from edge and shape ratios (documented formula in `docs/aspirational-splits.md`; no tuning parameters).

`sdi show --splits` reports current progress. `sdi trend --splits` reports progress over the snapshot window.

**Non-classification reinforcement:** `progress_score` is reported alongside the raw inputs that produced it. If a user asks "why is progress 0.3 not 0.7?" the answer is in the same JSON block. The score is a convenience scalar, not a verdict. `sdi check` does not read it.

Splits with past `target_date` and `progress_score < 1.0` surface a plain informational line: `split "billing → billing_core + invoicing" past target_date 2026-Q3 at progress 0.42`. No emoji, no severity. The user decides whether to extend the target or commit to finishing.

### 5.7 Change coupling surfacing

**v0 state.** `[change_coupling]` config exists (`min_frequency`, `history_depth`), but the metric surfaces only as a snapshot field. No diff or ranking.

**Phase B delta.** `sdi diff --coupling` reports:
- Pairs of files that co-changed in ≥`min_frequency` commits during the `history_depth` window, grouped by whether they are in the same Leiden cluster.
- Cross-cluster co-changing pairs are the interesting output: they are strong candidates for boundary revision (either split them apart or acknowledge the coupling in `allowed_cross_domain`).

Change coupling is *input to boundary reasoning*, not to drift verdicts. It does not contribute to any threshold. It surfaces in diff as a standalone section and in a new `sdi boundaries --coupling` subcommand that reports current co-change pairs against the ratified boundary spec.

### 5.8 Phase B acceptance

Phase B is done when:

- `sdi diff` hotspot ranking and `--attribute` mode ship with blame-based provenance. Integration test against `tests/fixtures/evolving/` verifies contribution accounting matches hand-computed values.
- `sdi explain <shape_id>` ships with nearest-neighbor search and history sparkline.
- `sdi diff --hints` and `sdi show --hints` emit rule-based hints with citations. Rule unit tests cover every rule.
- `.sdi/canonicals.yaml` spec shipped. Distance-to-canonical computed in `sdi diff` and `sdi explain`. Stale-canonical detection works.
- Aspirational split progress scalar computed and surfaced in `sdi show --splits` and `sdi trend --splits`.
- Change coupling surfaces in `sdi diff --coupling` and `sdi boundaries --coupling`.
- `sdi check` exit codes and threshold logic unchanged from v0. Integration test verifies no Phase B field affects gate verdict.
- Documentation: `docs/actionability.md` covers hotspot interpretation, attribution caveats (blame is not causation), and when to pin canonicals.

---

## 6. Phase C — Extensibility

Phase C opens SDI's analysis surface to user-supplied extensions without opening the determinism surface. Two mechanisms land: custom pattern categories (resolves OQ3) and cross-language contract-file inference (resolves OQ4). Neither is a general plugin system — both are narrow, declarative, and deterministic by construction.

### 6.1 Custom pattern categories (resolves OQ3)

**Mechanism.** Users drop tree-sitter query files into `.sdi/categories/*.scm` and a TOML manifest entry per category. No Python plugin API. No dynamic code loading.

**Directory layout:**
```
.sdi/
├── categories/
│   ├── repository_pattern.scm      # Tree-sitter query
│   ├── repository_pattern.toml     # Category metadata
│   ├── command_handler.scm
│   └── command_handler.toml
```

**Manifest fields (`*.toml`):**
```toml
[category]
name = "repository_pattern"
description = "Data access via a Repository abstraction"
languages = ["python", "typescript", "kotlin"]
query_file = "repository_pattern.scm"
min_pattern_nodes = 8
# Optional: explicit overlap declarations with built-in categories
overlaps_with = ["data_access"]
```

**Query file (`*.scm`):** Standard tree-sitter query syntax. One query file per category per target language, discriminated by sibling files (`repository_pattern.python.scm`, `repository_pattern.typescript.scm`). Missing language queries skip that language silently.

**Determinism preservation (enforcing P3):**
- Query execution is pure: tree-sitter's query engine is deterministic.
- Custom categories are loaded once at analysis start. Their content hash (SHA-256 of each `.scm` + `.toml`) is recorded in `snapshot.plugins.categories[*].content_hash`.
- A snapshot reproduces iff the same category set + same content hashes are present.
- Failed query compilation is a config error (exit 2). Partially loading some categories is not an allowed degraded mode.
- Custom categories that produce zero matches are still recorded in the snapshot with empty shape sets — "computed, empty" vs "not computed" distinction (§3.3 #4).

**Collisions with built-ins.** If a user's category name matches a built-in (`error_handling`), load fails with exit 2 and a clear message to rename. Built-in names are reserved. The `overlaps_with` field is descriptive (reported in `sdi catalog`); it does not change semantics — overlapping categories double-count shapes, which is the correct behavior because the shapes are real in both categories.

**Sandbox boundary.** Tree-sitter queries cannot execute arbitrary code. They cannot read the filesystem. They cannot make network calls. This is why tree-sitter queries are the plugin surface and a Python API is not — the sandbox is enforced by the query language itself.

**Documentation.** `docs/custom-categories.md` ships with a worked example (repository pattern in Python) and a debugging walkthrough using `sdi catalog --category repository_pattern --verbose` to see which AST nodes matched.

### 6.2 Cross-language contract inference (resolves OQ4)

**Mechanism.** SDI parses contract files (OpenAPI 3.x YAML/JSON, protobuf `.proto`, GraphQL SDL `.graphql`) and emits *synthetic contract nodes* in the dependency graph. Callers in any language reference contract nodes by stable id.

**Scope strictly limited to contract files.** SDI does not parse code to infer that a `fetch('/api/users')` call in TypeScript targets a `@router.get('/users')` route in Python. That is inference. Parsing the OpenAPI spec that both sides agree on is not inference — it is reading declared intent.

**Contract node ids.** Each contract element gets a stable id derived from the contract file path + element path:
- OpenAPI: `contract:openapi:<file>:<method>:<path>` (e.g., `contract:openapi:api/users.yaml:GET:/users/{id}`)
- protobuf: `contract:proto:<file>:<service>.<rpc>`
- GraphQL: `contract:graphql:<file>:<type>.<field>`

**Edge inference.** A code file that imports a generated client (`from users_client import get_user`) or contains a recognizable server-side binding (FastAPI `@router.get("/users/{id}")`, gRPC service implementation class, Apollo resolver) gets an edge to the corresponding contract node. Edge inference rules live in language adapters as declarative tables, not heuristics.

**New graph metrics enabled.**
- `contract_fan_in` per contract node: how many callers reference it.
- `contract_fan_out` per code file: how many contracts it depends on.
- Cross-module edges *through* contract nodes are reported in `sdi diff --coupling` with `via: contract:<id>`, making API-surface coupling visible.

**Boundary spec integration.** `.sdi/boundaries.yaml` gains an optional `contracts` section:
```yaml
contracts:
  - path: "api/users.yaml"
    owner: "users"              # Module that owns the contract
  - path: "api/billing.proto"
    owner: "billing"
```
When a contract has a declared owner, cross-module calls *through* that contract are reported as "via declared API" rather than flagged as coupling. Undeclared contracts surface as "contract with no declared owner" in `sdi boundaries --review`.

**Scope exclusions (held firm):**
- No parsing of language-level code to infer cross-language calls.
- No interpretation of URL string literals.
- No runtime tracing. No log parsing. No dynamic analysis.
- If a project has no contract files, cross-language inference contributes nothing and costs nothing.

**Budget impact.** Contract parsing is bounded by contract file count, not source file count. Typical projects have <50 contract files; parse cost is <5% of pipeline total.

### 6.3 Adapter plugin interface — deferred

A full plugin interface for *language adapters* (i.e., letting a user add an Elixir adapter without forking SDI) is tempting but deferred to post-v1. Adapters are deeper than category queries — they carry fingerprinting logic, symbol resolution, import resolution. Opening that as a plugin surface without a year of iteration on the adapter contract would ship determinism footguns. Post-v1 can revisit once the current six-to-nine language adapters have stabilized on a common internal shape.

### 6.4 Phase C acceptance

Phase C is done when:

- `.sdi/categories/*.scm` + `*.toml` loading is functional end-to-end. Integration test ships with a worked "repository pattern" custom category on the multi-language fixture.
- Content hashing of plugins populates `snapshot.plugins.categories[*].content_hash`; reproducibility tests confirm same-hash = same-output.
- Collision, compilation-failure, and missing-language-query error paths covered by unit tests with specific exit codes.
- OpenAPI 3.x, protobuf, and GraphQL SDL contract parsers ship. Synthetic contract nodes appear in the dependency graph. Three integration fixtures (one per contract type) verify edge inference against known-good outputs.
- `.sdi/boundaries.yaml` `contracts` section supported by schema and `sdi boundaries --review`.
- `docs/custom-categories.md` and `docs/cross-language-contracts.md` ship.
- Benchmark: Phase C additions must not exceed +15% cold pipeline time on the standard benchmark fixtures.

---

## 7. Phase D — Operator Ergonomics

Phase D is polish for operators — the people who wire SDI into CI, onboard teams, or run it against historical git ranges. Nothing in Phase D changes a metric. It changes how metrics are produced, consumed, and installed.

### 7.1 Historical backfill

**v0 state.** `sdi snapshot --commit REF` works for a single commit. Multi-commit backfill requires a user-written bash loop, which is fine for ad-hoc use but painful for onboarding a mature repo onto SDI.

**Phase D delta.** `sdi backfill` subcommand:

```
sdi backfill --since 2025-01-01 --every 1week
sdi backfill --commits HEAD~100..HEAD --every 5
sdi backfill --tags v0.*
```

Strategy selection:
- `--every <N>` with commit range: take every Nth commit.
- `--every <duration>` with date range: take the first commit of each period.
- `--tags <pattern>`: take commits matching tag pattern.

**Behavior.**
- Writes directly to `.sdi/snapshots/`. Respects retention (§16 of v0 rules). Default retention (100) means backfilling more than 100 snapshots without raising retention is a config error.
- Parallelizes at the commit level via `ProcessPoolExecutor` (one worker per commit, capped at `SDI_WORKERS`).
- Each commit's snapshot is self-contained — backfill does not use incremental caching across commits (the cache layer operates at the per-file parse level per commit, not across commits).
- Progress bar to stderr (per P2 of v0 §"Non-Negotiable Rules" #9). Never writes to stdout during backfill.
- Interrupt-safe: SIGINT stops at the next snapshot boundary, leaving already-written snapshots intact. The next `sdi backfill` with the same args resumes by skipping already-captured commits.

**Budget reality.** Backfill is inherently O(commits × pipeline cost). SDI does not promise it's fast; it promises it's correct, interrupt-safe, and observable.

### 7.2 GitHub Action

**v0 state.** v0 DESIGN.md explicitly defers a "polished GitHub Action" to post-v0. Manual CI integration (`pip install sdi && sdi check`) is documented.

**Phase D delta.** Ship `geoffgodwin/sdi-action@v1` as a thin wrapper:

```yaml
- uses: geoffgodwin/sdi-action@v1
  with:
    command: check        # default: check; also supports: snapshot, diff
    fail-on-exceeded: true  # default: true; pass through `sdi check` exit 10
    pr-comment: true        # default: false; render diff summary as PR comment
    artifact-snapshot: true # default: false; upload latest snapshot as workflow artifact
```

**Non-negotiable constraints for the Action:**
- The Action installs a *pinned* SDI version. Users specify in `with: version: 1.1.0`. No "latest" default — that would make runs irreproducible.
- PR comment rendering reuses `sdi diff --format text` output, unmodified. No separate comment formatter.
- The Action does not write to snapshot storage in the repo unless the user's workflow explicitly commits the artifact — SDI's principle is that snapshots are real git-tracked files the user owns.

**Why this is safe to ship in v1 vs. being post-v0.** v0's reasoning was that the CLI and schema were still moving. By Phase D, Phase 0 has frozen schema v1 (§3.3) and Phases A/B have stabilized `sdi diff` output format. The inputs to a reusable Action are now stable enough to ship.

### 7.3 `sdi diff` stdin support

**v0 state.** Both snapshot arguments are file paths.

**Phase D delta.** `sdi diff - <file>` or `sdi diff <file> -` reads one snapshot from stdin. Enables pipelines like `gh release view --json <x> | jq '.body.snapshot' | sdi diff - .sdi/snapshots/latest.json` for cross-release comparisons.

The hyphen convention is Unix standard; implementation is a small change in the argument parser plus mimicking the snapshot loader to accept a stream. Malformed stdin input exits with code 3 (analysis error), consistent with v0 error taxonomy.

### 7.4 `sdi config` read-only subcommand

**v0 state.** v0 DESIGN.md explicitly rejects a `sdi config` management subcommand.

**Phase D delta.** Adds a *read-only* inspection subcommand:

```
sdi config show           # Render the effective config with source annotations
sdi config sources        # List config files discovered and their precedence
sdi config validate       # Validate config without running anything
```

**Scope held firm:** No `sdi config set`, no `sdi config init` beyond what `sdi init` already does, no interactive editing. The command reads and reports. Users edit `.sdi/config.toml` directly with their editor.

Source annotations look like:
```
[core]
languages = "auto"          # default
exclude = [...]             # .sdi/config.toml:5
random_seed = 42            # default

[thresholds]
pattern_entropy_rate = 2.5  # SDI_PATTERN_ENTROPY_RATE (env)
...
```

This answers "where is this value coming from?" — a recurring onboarding question once project, user, and env-var configs stack up. Pure reporting, no mutation. `sdi config` never writes.

### 7.5 Standalone binary distribution

**v0 state.** Deferred. Tree-sitter grammar loading from bundled binaries has known complexity.

**Phase D delta.** Ship `sdi-bin` standalone binaries for linux-x86_64, linux-aarch64, darwin-x86_64, darwin-aarch64 via PyOxidizer or equivalent. Windows remains best-effort and may slip to post-v1.

**Grammar handling:** Default grammar set is bundled into the binary. Adding languages beyond the default set requires the `pip install` path. This is a deliberate trade-off: the binary is for quick adoption and CI use; users with exotic languages continue to use the Python package.

**Version drift prevention:** The binary's `sdi --version` output explicitly reports `sdi 1.0.0 (standalone, grammars: py,js,ts,go,java,rust,bash,c,cpp,ruby,kotlin)` so users can distinguish installations. Integration test verifies the binary produces byte-identical snapshot JSON to the pip-installed version on the standard fixtures.

### 7.6 Shell completion refinements

**v0 state.** M11 shipped completion scripts.

**Phase D delta.** Adds dynamic completions:
- `sdi explain <TAB>` completes fingerprint ids from the latest snapshot.
- `sdi show --category <TAB>` completes category names (built-ins + custom from `.sdi/categories/`).
- `sdi diff <snapshot> <TAB>` completes snapshot filenames from `.sdi/snapshots/`.

These require shell-specific hooks (bash, zsh, fish) that shell out to `sdi complete <context>` — a new hidden subcommand that emits completion candidates to stdout. Candidates are computed from local files only, no network, no heavy computation.

### 7.7 Phase D acceptance

Phase D is done when:

- `sdi backfill` ships with all three strategies, parallel execution capped at `SDI_WORKERS`, resumable on SIGINT. Integration test uses `tests/fixtures/evolving/` to verify N backfilled snapshots match N snapshots from an equivalent loop.
- `geoffgodwin/sdi-action@v1` published to the GitHub Actions Marketplace. Uses pinned SDI version. PR comment rendering verified in a test workflow.
- `sdi diff` accepts stdin via `-`. Unit test verifies stream and file inputs produce identical outputs.
- `sdi config show|sources|validate` ship as read-only. `sdi config set` is confirmed absent (integration test).
- Standalone binaries built for four platforms with bundled grammars. Byte-identical snapshot integration test passes.
- Dynamic shell completions work in bash, zsh, fish for the three completion points listed.
- No Phase D change modifies a snapshot field or a metric value.

---

## 8. Explicitly Rejected — Restated With v1 Rationale

Two items from v0's "What Not to Build Yet" were not merely deferred — they were rejected on principle. v1 restates the rejections and sharpens the rationale with a year of adopter experience. The rejections stand.

### 8.1 Watch mode / file-watcher daemon — *still rejected*

**v0 reason:** "Violates the Unix philosophy constraint."

**v1 restated reason:** Watch mode is not just a style choice; it creates three failure modes SDI cannot absorb:

1. **Re-parsing half-saved files.** Editors write files non-atomically. A file watcher fires on the write event before the editor finishes; SDI would parse a syntactically invalid intermediate state and either fail (generating noise) or silently skip (generating gaps). Users would then calibrate to a watcher that is sometimes wrong in unpredictable ways.
2. **Debounce is an opinion.** Every watcher needs a debounce window. The "correct" window depends on editor behavior, filesystem, OS. Shipping one value is a heuristic dressed as a default.
3. **Watch mode is a gateway to daemon mode.** Users who accept "sdi is watching the tree" will next ask for "sdi is answering queries over a socket" — which is a full daemon, which is a product category SDI is not.

**v1 answer to the latent demand.** The real underlying want is "faster feedback on my change." v1 satisfies that via:
- Fast incremental parse cache (M10, v0) — a re-run touching 3 files is already sub-second.
- `sdi snapshot --paths src/billing/` — scoped snapshots for rapid iteration on one area.
- `sdi diff HEAD~1 HEAD` patterns in pre-commit hooks.

IDE/editor integration (a plugin that renders the diff in a side-panel) is *not* rejected — it is a v2 concern (§10). An editor plugin is a client of SDI's output, not a new execution mode inside SDI.

### 8.2 Automatic drift-vs-evolution classification — *still rejected*

**v0 reason (KD1):** "Requires opinionated heuristics and creates dangerous false negatives in CI gates."

**v1 restated reason:** A year of thinking has made the argument sharper, not weaker:

1. **A classifier is a suppressor.** A "this is a migration, not drift" verdict inevitably informs whether to gate or not gate. SDI has one gate (`sdi check`) and it reads declared thresholds with explicit expiry dates. Adding a classifier that affects gating would smuggle suppression back in, undoing v0's §"Non-Negotiable Rules" #5 ("SDI never suppresses alerts automatically").
2. **The user has the cheaper evidence.** Whether a given velocity vector is a migration or drift is a fact the engineering team knows in seconds and SDI would spend compute trying to recover. The ratio of SDI's inference cost to the user's stated-intent cost is unfavorable by orders of magnitude. The solution is `[thresholds.overrides.*]` — you say it, we record it, we enforce the expiry. You are already in the loop.
3. **False positives here are quiet.** Unlike a parse error, a classifier marking drift as migration silently disables the signal the user installed SDI to get. The failure mode is invisible until an incident reveals that the drift detector stopped detecting drift six months ago.

**v1 answer to the latent demand.** Phase B's actionability surfaces (hotspots, attribution, neighbors, canonical distance, split progress) give the user the evidence a classifier would have consumed. The user classifies. SDI serves the evidence.

If a post-v1 version ever adds classification, it must be opt-in, advisory-only (never gate), and documented as a hint — never as a verdict. Even that is a v2 conversation, not a v1 one.

---

## 9. Additions to Non-Negotiable Rules

The v0 non-negotiable rules all stand. v1 adds six, numbered continuing v0's list (v0 ended at #16 in CLAUDE.md; v1 adds 17–22 to avoid renumbering). These are shipped constraints, not goals.

**17. Cycle enumeration is always capped.** The `sdi.graph.metrics` module never calls `simple_cycles()` without a cap. `max_cycles` and `time_budget_ms` are read from config; defaults are `1024` and `2000`. A truncated run records `graph.cycles_truncated = true` in the snapshot. (Phase 0 §3.1.)

**18. Plugin content hashes are recorded in every snapshot.** Any custom-category `.scm` or `.toml` file contributing to analysis has its SHA-256 recorded under `snapshot.plugins.categories[*].content_hash`. A snapshot is reproducible iff the same plugin set is loaded with the same hashes. (Phase C §6.1, P3.)

**19. Advisory fields never gate.** `sdi check` reads only fields under `thresholds.*` and `threshold_results.*`. It must not read `hints`, `neighbors`, `explanations`, `attributions`, or `progress_score`. This is enforced by an integration test that strips all advisory fields from a snapshot and verifies `sdi check` produces the same exit code and output. (P4.)

**20. Schema extensions are additive within a major version.** v1 snapshots (schema `2`) never rename or remove fields across v1.x releases. Fields may be deprecated (documented as such) but continue to be populated. Removing a field requires schema `3` and a major version bump. (§3.3.)

**21. Classification verdicts are never emitted.** SDI's output never contains the strings "drift," "migration," "violation," "problem," or any synonym asserting a quality judgment *about the codebase*. (Status flags like "exceeded" or "override active" describe SDI's own measurement state, which is fine.) A PR that introduces such a string in user-facing output is rejected. (P2, v0 Rule #4.)

**22. Attribution is raw, not interpreted.** Git blame output in `sdi diff --attribute` is passed through without commentary. SDI does not combine author + shape + category into "author X is introducing drift" narratives. The user reads the blame, the user concludes. (P1, P2.)

---

## 10. Performance Budgets

v0 documented targets. v1 enforces them via benchmarks in CI on release-candidate tags (not every PR — that's too slow).

### 10.1 Baseline reference

The reference workload is the v0 benchmark suite at `tests/benchmarks/` against `tests/fixtures/evolving/` at its latest commit, measured on GitHub Actions `ubuntu-latest` with `SDI_WORKERS=2`. v1.0.0-rc.1 establishes the v1 baseline; subsequent v1.x releases measure against that.

### 10.2 Per-phase budget ceilings

| Phase | Feature | Ceiling (vs. v1 baseline) |
|---|---|---|
| Phase 0 | Cycle detection cap | Neutral or negative (cap cannot make typical case slower). |
| Phase A | 3 new language adapters | +0% on projects not using them. Per-adapter cost bounded by file count. |
| Phase A | 4 new pattern categories | +20% cold parse time ceiling. |
| Phase A | Fingerprint tier (both tiers) | +10% fingerprinting stage. |
| Phase A | Generated-code auto-detection | +3% cold parse time. |
| Phase B | Hotspot ranking (no `--attribute`) | +2% diff time. |
| Phase B | `sdi diff --attribute` (blame) | Not in default path. Unbounded by design (opt-in). |
| Phase B | `sdi explain` | Not in default path. |
| Phase B | Canonical distance | +5% diff time when canonicals present. |
| Phase B | Aspirational split progress | +3% snapshot assembly. |
| Phase C | Custom categories (per category) | +3% parse time per loaded category. |
| Phase C | Contract file parsing | +5% cold time on projects with ≤50 contract files. |
| Phase D | `sdi backfill` | O(commits × pipeline cost). Not a regression target — this is a new command, budgeted at the call site. |

**Cumulative ceiling:** The sum of all Phase 0–D budgets on a project using every feature is ≤+50% cold pipeline time. Projects not using optional features see less. Exceeding the cumulative ceiling is a release blocker; individual budgets can be renegotiated with a maintainer sign-off in the PR.

### 10.3 Memory budgets

v0's constraint holds: memory usage is proportional to the largest single file, not total codebase size (v0 Rule #15). v1 additions must preserve this. Specifically:
- Pattern fingerprint tier storage: both tiers are small (~100 bytes per fingerprint). Not a memory concern.
- Contract node graph additions: contract nodes are small; not a concern.
- `sdi explain` neighbor search: loads the full pattern catalog for the target category (typical: <10k entries). Bounded.
- `sdi backfill`: per-commit memory is bounded by single-snapshot memory. Parallel workers multiply by `SDI_WORKERS`, which is the documented behavior.

No v1 feature loads multiple snapshots simultaneously except `sdi diff` and `sdi trend` — and those are v0 behavior.

### 10.4 Disk budgets

Snapshots grow under v1 because more fields are populated. Per-snapshot size estimates:

| Schema | Typical size | Large project (1M LOC) |
|---|---|---|
| v0 | 10–30 KB | 50–80 KB |
| v1 (all features on) | 20–60 KB | 100–200 KB |

With default retention of 100 snapshots, maximum `.sdi/snapshots/` footprint is ~20 MB for large projects under v1. Acceptable. If adoption brings projects with larger footprints, retention is already user-configurable.

---

## 11. Testing Strategy Updates

v0's strategy (unit + integration + benchmarks, 80% unit coverage, fixtures over mocks for integration) stands. v1 adds:

### 11.1 Reproducibility contract tests

Every phase lands a "same inputs = same outputs" test:
- Phase 0: `sdi snapshot` on identical commit + config + boundaries produces byte-identical JSON (already implicitly tested; made explicit and added to the "required for every release" set).
- Phase A: Generated-code auto-detection is deterministic given the same file content.
- Phase B: Hotspot ranking and `sdi explain` outputs are deterministic across runs.
- Phase C: Custom category loading with identical content hashes produces identical shape counts. Contract parsing is deterministic.
- Phase D: Backfill of the same commit range in different runs produces byte-identical snapshot sets.

### 11.2 Schema migration tests

A fixture set of v0-schema snapshots (captured at v0.14.0, the last v0-era release) lives in `tests/fixtures/snapshots-v0/`. Every v1 release runs:
- v1 readers process v0 snapshots without error.
- `sdi diff <v0-snapshot> <v1-snapshot>` produces a result flagged `cross_schema_version = true` and treats the v0 snapshot as a baseline (no delta).
- `sdi trend` with a mix of v0 and v1 snapshots reports per-snapshot schema version alongside each data point.

### 11.3 Plugin isolation tests

Phase C introduces user-loaded content. The test suite must verify:
- A malformed `.scm` file fails loading with exit 2 and a specific error message (not a stack trace).
- A custom category with a name colliding with a built-in fails loading with exit 2.
- Content-hash changes produce observable snapshot changes (same category with a modified `.scm` yields a different `plugins.categories[*].content_hash`).
- Tree-sitter query execution does not read the filesystem outside its input source buffers. Verified by a test that runs category queries with a mocked filesystem and confirms no file access beyond the parser buffer.

### 11.4 Non-gating assertion

An integration test strips all advisory fields (`hints`, `neighbors`, `explanations`, `attributions`, `progress_score`) from a snapshot and runs `sdi check` against a threshold config with and without the strip. Both runs must produce identical exit codes and output — any difference is a P4 violation.

### 11.5 Performance regression gates

`tests/benchmarks/` runs on release candidates. A regression over the declared phase ceiling (§10.2) without an accompanying budget update in the PR blocks the release. Benchmarks run with fixed worker count (2), fixed seed (42), and a warmed page cache; three runs; median time reported.

### 11.6 Cross-platform reproducibility

The standalone binary (Phase D) must produce byte-identical snapshot JSON to the pip-installed version on the same fixture. Tested on linux-x86_64 and darwin-x86_64 in CI. Divergence is a release blocker. (This catches subtle issues like platform-specific hash orderings or path separator leaks into fingerprints.)

---

## 12. Versioning and Release Strategy

SDI uses **MAJOR.MILESTONE.PATCH** semantic versioning. The three positions map to the three units of work the project produces:

- **MAJOR** = the design era. Increments when a new DESIGN document is ratified (DESIGN_v0 → DESIGN_v1 → DESIGN_v2 …). Every cross-era release is a MAJOR bump because the design contract changed.
- **MILESTONE** = the position of the milestone within the current MAJOR — `1` for the first milestone shipped in the era, `2` for the second, and so on. **The counter starts over at every MAJOR bump.** Versions within a MAJOR are dense: `X.0.0`, `X.1.0`, `X.2.0`, `X.3.0` … with no gaps.
- **PATCH** = a bugfix, drift fix, or ad-hoc / human-note correction against a shipped milestone. Increments per fix; resets to 0 on every new MILESTONE.

Milestone files under `.claude/milestones/` (`m01-*.md`, `m02-*.md`, …) follow the same per-era numbering as the version's MILESTONE position. When a new MAJOR cuts, the previous era's milestone files are retired (archived or deleted — see §12.5) and the new era starts fresh at `m01-*.md`. The MILESTONE position in the version equals the milestone file number, always.

### 12.1 Version era boundaries

- **0.x** — v0 era (DESIGN_v0, the original scaffold). 14 milestones (files `m01-*.md` through `m14-*.md`) shipped as `0.1.0` … `0.14.0`. Final v0 release is `0.14.x`. Bugfix patches against 0.14 are `0.14.1`, `0.14.2`, … No further MILESTONE bumps in the v0 era — v0 is closed for new work.
- **1.x** — v1 era (this document). Cuts `1.0.0` when DESIGN_v1 is ratified and the v0 → v1 lifecycle/CI/docs work is complete (see §12.2). At the cut, v0 milestone files are retired and the v1 milestone counter restarts. The first v1 milestone is the new `m01-*.md`, shipping as `1.1.0`. The second is `m02-*.md` → `1.2.0`. And so on.
- **2.x** — v2 era (DESIGN_v2, future companion surfaces — see §13). Cuts `2.0.0` when DESIGN_v2 is ratified. Counter resets again: first v2 milestone is `m01-*.md` → `2.1.0`.

### 12.2 Cut criteria

A version is cut when the work behind its position is complete and validated:

- **MAJOR cut (`X.0.0`)** — DESIGN_vX is ratified and merged. The CI/CD/docs/release-pipeline lifecycle work for the new era has landed. No milestones under the new design have shipped yet; the cut is a checkpoint, not a feature drop.
- **MILESTONE cut (`X.M.0`)** — Milestone M's acceptance criteria are met, tests pass on CI, CHANGELOG entry written. The previous milestone's outstanding patches (if any) are folded into the milestone summary.
- **PATCH cut (`X.M.P`)** — One or more bugfixes, drift fixes, or human-note corrections have landed since the last MILESTONE cut. Ship cadence is "when there's enough to ship and nothing in flight."

**Pre-1.0 cement-the-moment cut:** `0.14.0` is cut after this lifecycle PR lands, even though M14 was already complete, to mark the moment the v0 era closed and to exercise the release pipeline against a known-good state before v1 development begins. Subsequent v0 fixes are `0.14.1` etc. until the v1 era cuts.

### 12.3 Release tagging and notes

- Tags are prefixed with `v` (e.g., `v0.14.0`, `v1.0.0`, `v1.1.0`).
- `CHANGELOG.md` follows Keep a Changelog. Every release has an entry under its version heading. Every entry is structured as *Added / Changed / Deprecated / Removed / Fixed / Security*.
- Every non-additive change gets a `Deprecated` entry in the prior MILESTONE release, minimum.
- Tekhton automation: a milestone commit does not bump the version on its own — version bumping is a deliberate release act with a CHANGELOG cut. Drafts of CHANGELOG entries land in `[Unreleased]` during milestone development; they are promoted into a versioned section at release-cut time.

### 12.4 Backward compatibility guarantees within a MAJOR

Within the same MAJOR (e.g., across all 1.x releases):

- Snapshot schema: additive-only (§3.3).
- CLI verbs: never removed. New verbs land additively.
- CLI flags: never removed within a MAJOR; flags may be deprecated with a warning for one MILESTONE before removal in the next MAJOR.
- Exit codes: stable from v0 (§v0 Rule #8). Cross-era stable.
- Config keys: never repurposed (v0 Rule #12). New keys with safe defaults; removed keys produce a deprecation warning.

A breaking change to any of the above requires a MAJOR bump. Because MAJOR is tied to a new DESIGN document, breaking changes are deliberate, documented, and infrequent.

### 12.5 1.0.0 cut criteria

`1.0.0` is the inflection point between the v0 scaffold era and the v1 actionability era. Cut criteria:

1. DESIGN_v1 (this document) merged on `main`.
2. Lifecycle/CI/docs work shipped: release workflow, GH Pages, version single-sourcing, branch protection, Tekhton version-files wiring (the work this DESIGN section is about).
3. `0.14.0` released and battle-tested for ≥1 round of real-world use; any drift surfaced patched into `0.14.x`.
4. No outstanding `[Unreleased]` items in `CHANGELOG.md` from the v0 era.
5. **v0 milestone files retired.** The 14 v0 milestone files (`.claude/milestones/m01-*.md` through `m14-*.md`) and the v0 entries in `MANIFEST.cfg` are removed from the active milestone directory. The MILESTONE_ARCHIVE.md retains the historical record. Tekhton's `pipeline.conf` is repointed at `DESIGN_v1.md`. After this step, the active milestones directory is empty and ready for v1 work to populate it as `m01-*.md`, `m02-*.md`, ….

`1.0.0` does not require any v1-era milestone to have shipped. It marks the era boundary; the first v1-era milestone ships separately as `1.1.0`.

### 12.6 Deprecation policy

A deprecation lifecycle is:
1. **Announce** — Deprecation entry in `CHANGELOG.md` for release N. Feature still works; emits warning on stderr.
2. **Maintain** — Feature continues to work for one additional MILESTONE release.
3. **Remove** — Feature removed in the next MAJOR. Release notes call it out in `Removed`.

No "silent deprecation." No deprecation without a replacement path documented.

---

## 13. What Not to Build Yet — Seeds for v2

v1's job is to make the measurements actionable. v2's job is to *close the loop* — SDI acting on the user's behalf, and SDI's metrics living where teams already work. This section is not a v2 design document. It is a list of capabilities v1 must deliberately *not* build, so the v2 design has clean ground.

Each item names the capability, why it belongs in v2 (not v1), and what v1 must *not* accidentally ship that would constrain v2's shape.

### 13.1 Companion dashboard / hosted UI

**Why v2, not v1.** SDI produces JSON that already feeds Grafana, Datadog, and any dashboard that consumes structured data. A *first-party* dashboard is a separate product surface: it has UX, hosting, auth, access-control, billing — none of which overlap with the CLI's concerns. Shipping a v1 dashboard would pull maintenance energy from the CLI at exactly the moment the CLI is growing new capabilities (Phases A–D).

**What v1 must not ship that would constrain v2.**
- v1 must not introduce a "default dashboard export format" that differs from the snapshot schema. The snapshot JSON *is* the export format. A dashboard reads snapshots; it does not receive a parallel serialization.
- v1 must not ship any command that pushes data to a remote endpoint, even optionally. The "no network calls during analysis" rule (v0 Rule #1, v1-restated in §8.1) holds absolutely for the CLI. If v2 adds a push command, it lives outside the `sdi` analysis pipeline — likely as a separate `sdi-publish` binary with explicit user invocation.

**v2 seed.** A companion surface (`sdi-web` or similar) that reads `.sdi/snapshots/` and renders trends, hotspots, and boundary divergence in a browser. Self-hosted first; hosted SaaS is a third-order concern.

### 13.2 Gardener agent / auto-remediation

**Why v2, not v1.** v1's P2 ("No classification creep") and v1 Rule #21 ("Classification verdicts are never emitted") make it impossible for v1 to decide *what* to fix. An agent that generates consolidation PRs requires exactly that decision — pick a shape, pick the shapes it replaces, pick the files, generate the diff. That is a generative act. SDI is a measurement instrument. The generative act belongs in a companion product.

**What v1 must not ship that would constrain v2.**
- v1 must not emit remediation output that is *executable* — e.g., patch files, AST rewrites, code snippets. Hints (§5.4) are advisory text citing snapshot fields; they are not prescriptions.
- v1 must not add fields to the snapshot schema that implicitly rank shapes as "should be consolidated." Canonical pinning (§5.5) is user-declared intent, not SDI-inferred preference.
- v1 must not introduce "remediation state" — a machine-readable record of which shapes SDI proposed to consolidate. That is state the gardener agent will want; introducing it in v1 forces a design without feedback from the agent's real needs.

**v2 seed.** A gardener (likely LLM-backed, since the act is generative) that reads SDI snapshots and proposes consolidation PRs. The LLM lives in the gardener, not in SDI. SDI remains deterministic; the gardener does not.

### 13.3 IDE / editor plugin

**Why v2, not v1.** An IDE plugin is a *client* of SDI, not a new execution mode. It needs: a stable on-disk snapshot schema (Phase 0 §3.3 delivers this), a stable diff output format (Phases A/B stabilize this), and a reliable way to run `sdi snapshot --paths <current-file>` quickly (Phase A's fingerprint tier and existing M10 cache deliver this). All prerequisites land in v1. The plugin itself — VS Code extension, JetBrains plugin, Neovim integration — is client work.

**What v1 must not ship that would constrain v2.**
- v1 must not add an "IDE mode" to the CLI that changes output formatting for tooling. Stdout is data, stderr is logs (v0 Rule #9). An IDE consumes the JSON mode like any other client.
- v1 must not ship a language server. SDI is not an LSP implementation. An IDE plugin may *spawn an LSP* on top of SDI, but that is plugin work, not CLI work.

**v2 seed.** VS Code extension that renders hotspots inline, surfaces `sdi explain` output in a hover panel, and triggers `sdi snapshot --paths <file>` on save.

### 13.4 Auto-remediation PRs from CI

**Why v2, not v1.** This is a sub-capability of the gardener (§13.2) deployed into the CI loop. Same reasoning.

**What v1 must not ship that would constrain v2.** The GitHub Action (§7.2) must not grow PR-writing features in v1. It *reads* and *reports*. Writing is a post-v1 capability with its own review and safety model.

### 13.5 Distributed-systems structural divergence

**Why v2, not v1.** The blog post's Part 3 (referenced but unpublished) gestures at applying SDI's thinking to *inter-service* drift — the structural divergence between microservices, measured via API contracts, deployment topology, and observability data. This is a different product. v1's Phase C (contract-file inference, §6.2) lays the measurement groundwork inside a single repository. Taking the same ideas across services requires: cross-repo snapshot aggregation, service registry integration, trace/log ingestion, deployment-graph awareness. None of that is a CLI tool; it is a platform.

**What v1 must not ship that would constrain v2.**
- v1 must not introduce cross-repo snapshot aggregation. Snapshots live in `.sdi/snapshots/` per repo. Merging snapshots from multiple repos is a v2 platform concern.
- v1 must not add service-identity fields to snapshots. A snapshot describes a *tree*, not a *service*. If a tree happens to be one service's monorepo, that is a user-level fact, not something SDI asserts.
- v1 must not introduce OpenTelemetry / tracing integration. Deterministic static analysis stays that way.

**v2 seed.** A companion product that correlates per-repo SDI snapshots with service topology. Likely a separate repository, likely a separate binary, likely requiring infrastructure (object storage, a registry). Entirely separate from `sdi`.

### 13.6 Companion technical paper

**Why v2, not v1.** The blog post is a narrative introduction; a technical paper would document the mathematical foundations (entropy formulation, Leiden gamma selection, fingerprint hash space, partition stability theorem if one exists). It is a valuable artifact but deferred until v1 has shipped and collected enough adopter data to ground the claims empirically rather than theoretically.

**What v1 must not ship that would constrain v2.** Nothing concrete — this is a documentation deliverable. But: v1 development should keep notes on surprising empirical findings (gamma distributions observed in the wild, hash collision frequencies, partition stability behaviors under known codebase shapes), because those observations are exactly what a paper would be built from.

### 13.7 Custom language adapter API

**Why v2, not v1.** Phase C ships custom *pattern categories*, not custom *language adapters*. Adapters are deeper; they carry fingerprinting logic, symbol resolution, import resolution. A plugin API for adapters is premature — the adapter contract is still settling as new languages land in Phase A.

**What v1 must not ship that would constrain v2.** v1 must not commit publicly to a specific adapter plugin shape. Internal adapter refactoring in v1 (making adapters more uniform as Phase A adds C/C++, Ruby, Kotlin) is welcome; a public plugin ABI is not.

### 13.8 Interactive boundary ratification UI

**Why v2, not v1.** Current boundary ratification is edit-the-YAML. Users have asked (informally) for an interactive review mode where SDI proposes boundaries and the user accepts/rejects them one at a time. This is a UX layer over existing capability — natural for a dashboard (§13.1) or IDE plugin (§13.3), out of scope for the CLI.

**What v1 must not ship that would constrain v2.** The CLI must not grow an interactive prompt mode. The TUI constraint (v0 "Banned Anti-Patterns") holds. `sdi boundaries --suggest` emits the proposal as stdout data; a client can read it and render a UI, but SDI does not render UIs.

---

## 14. v1 Open Design Questions

v1 resolves v0's OQ1–OQ7 (§3.2) but opens its own questions. Each is a deferred decision awaiting data from Phase A–D adopter usage. Documented here so they do not silently become defaults by omission.

### OQ-v1-1. Fingerprint tier default

Phase A ships both `structural` and `named` fingerprint tiers (§4.3). The default for `sdi diff` summary output remains `structural` for v0 backward-compatibility, but `named` produces better hotspot rankings in practice (fewer false collisions).

**Question.** Should `named` become the default in v1.x or v2?

**Decision framework.** Collect hotspot false-positive reports from adopters (where a "new shape" flagged by `structural` is actually an existing shape that differed only in identifier naming). If false-positive rate exceeds 10% of reported hotspots across ≥5 projects, flip default to `named` in v1.x minor release with one-minor deprecation of `structural` as default (still computed, just not default).

**Closed by.** v1.x minor post-Phase A adoption data.

### OQ-v1-2. Hints rule set scope

Phase B ships rule-based hints (§5.4) with an initial rule set. The rule set could grow unboundedly. Should hints stay a small, curated set or accept community-contributed rules?

**Decision framework.** Track which hints adopters report as useful vs. noisy. Useful hints cited in `sdi explain`/`sdi diff` output in the wild (observable via adopter feedback) stay in. Noisy hints (reported as "I would turn this off if I could") get a config knob to disable by rule id, and if disabled by >50% of adopters, the rule is removed. Community contribution is deferred until the core set has stabilized.

**Closed by.** Observation over ≥6 months of Phase B adoption.

### OQ-v1-3. Contract file auto-discovery

Phase C parses OpenAPI, protobuf, GraphQL SDL (§6.2). Should SDI auto-discover contract files by extension + content signature, or require explicit declaration in config?

**Leaning.** Auto-discover, with an `--no-auto-contracts` opt-out and a `sdi show --contracts` surface listing discovered contracts so users can audit. Consistent with v1's "safe defaults" posture (e.g., generated-code auto-detection §4.4).

**Decision framework.** Ship auto-discovery in Phase C. If false-positive discoveries (files matching extension but not actually contracts) exceed a reasonable frequency in adopter feedback, reconsider the signature heuristics or move to explicit declaration.

**Closed by.** Phase C initial release + 3 months adopter feedback.

### OQ-v1-4. `sdi backfill` resumption model

Phase D ships `sdi backfill` with SIGINT resume-by-skip (§7.1). Alternative: a resume file that tracks partial progress. The resume file is more robust (handles crashes mid-snapshot) but is additional state on disk with its own failure modes.

**Decision framework.** Ship skip-based resumption first. If adopter reports indicate crashes mid-snapshot produce corrupted state (atomic write should prevent this — the crashed snapshot simply doesn't exist), no change needed. If edge cases emerge, revisit with a resume file.

**Closed by.** Phase D release + adopter experience.

### OQ-v1-5. Canonical pinning enforcement level

Phase B's canonical pinning (§5.5) is strictly advisory. Some adopters will ask for it to *enforce* — e.g., `sdi check` fails if a non-canonical shape appears in a category with a pinned canonical.

**Leaning.** Keep advisory. Making canonicals enforcing turns them into a classification mechanism (v1 Rule #21) — the tool would be declaring "this shape is wrong because it's not canonical."

**Decision framework.** If adopter demand for enforcement is consistent and principled (not just "we want a lint"), consider adding `sdi check --strict-canonicals` as an opt-in gate in v1.x. The gate would read user-declared canonicals, not SDI-inferred preferences, so it does not violate the classification rule. Ship advisory first; revisit on demand.

**Closed by.** v1.x minor post-Phase B adoption.

### OQ-v1-6. Standalone binary grammar set

Phase D ships standalone binaries with bundled grammars (§7.5). The bundled set is currently "v0 grammars + Phase A additions." Should the binary also bundle the most common *custom* tree-sitter grammars (e.g., `tree-sitter-toml`, `tree-sitter-yaml`) for contract-file parsing?

**Decision framework.** Bundle the grammars Phase C's contract parsers need (protobuf, GraphQL SDL). OpenAPI is JSON/YAML and handled by stdlib + ruamel.yaml, so no additional grammar needed. Do not grow the bundled set beyond analysis needs.

**Closed by.** Phase D release — decision forced by the binary build step.

---

## 15. Resolved Design Decisions (v1 Additions)

These are v1's counterparts to v0's KD1–KD10. Numbered continuing from v0 (v0 ended at KD10; v1 adds KD11–KD20).

**KD11. Phased rollout over big-bang release.**
v1's scope is too large for a single release. Phase 0 → A → B → C → D ships incrementally across the 1.x minor releases (one minor release per milestone — see §12). Each phase has independent acceptance criteria. This preserves adopter trust (no "upgrade and rediscover the tool") and keeps PR review manageable.

**KD12. Tree-sitter queries, not Python plugins, for custom pattern categories.**
Resolves v0 OQ3. Python plugins would create an unbounded determinism surface (§P3). Tree-sitter queries are declarative, sandboxed, and deterministic by construction. Trade-off: some pattern shapes are hard to express as queries; those shapes wait for a more capable mechanism (post-v1).

**KD13. Contract files, not code-level inference, for cross-language dependencies.**
Resolves v0 OQ4. Parsing OpenAPI/protobuf/GraphQL is reading declared intent. Inferring that `fetch('/api/users')` in TS targets `@router.get('/users')` in Python is inference. v1 does the first, never the second.

**KD14. Dual-mechanism generated code tagging (explicit list + advisory auto-detection).**
Resolves v0 OQ5. Explicit list (`.sdi/generated.txt`) is authoritative and excludes files from metrics. Auto-detection is advisory and surfaces candidates for promotion. Auto-detected files still contribute to metrics until explicitly listed. User is in the loop.

**KD15. Schema v1 frozen at Phase 0, additive-only thereafter.**
Resolves v0 OQ7. Trend data is the product; schema migrations that lose history destroy the product. Schema v1 is defined in `docs/snapshot-schema-v1.md` and JSON-Schema-validated in tests. Non-additive changes require schema v2 and a major version bump.

**KD16. Attribution is raw blame; SDI does not narrate.**
Phase B attribution surfaces file, line, commit, author, timestamp — all raw git metadata. SDI does not synthesize "author X is introducing drift" narratives. User reads the raw data, user concludes. This is v1's primary safeguard against P2 (classification creep).

**KD17. Canonicals are user-declared intent, not tool-inferred preferences.**
`.sdi/canonicals.yaml` records human choices. SDI never auto-promotes a shape to canonical based on prevalence. SDI could — the data supports it — but doing so would make SDI opinionated about what patterns are "good."

**KD18. Advisory fields are namespaced and checked to not gate.**
Phase B fields `hints`, `neighbors`, `explanations`, `attributions`, `progress_score` are grouped under advisory namespaces. `sdi check` is integration-tested to ignore them (§11.4). This makes the gating contract trivially auditable and lets advisory surfaces evolve without destabilizing gate behavior.

**KD19. Performance budgets are per-phase and enforced at release.**
v0 documented targets; v1 enforces ceilings via benchmark gates on release candidates (§10.2). Each phase declares its budget; cumulative ceiling is +50% cold pipeline time with all features on. Exceeding ceilings without maintainer sign-off blocks release.

**KD20. CLI remains the product through v1; companion surfaces are v2.**
v1 ships no dashboard, no agent, no IDE plugin, no cross-repo aggregation. Those are v2 concerns (§13). v1's job is to make the CLI's measurements actionable inside a single repo. v2 builds outward from that foundation — across repos, into editors, into generative loops.

---

## Appendix A — Milestone Seed List

Non-binding — the milestone authoring (Tekhton) will refine, split, and sequence. This is a skeleton of what the v1 milestones should cover.

After the `1.0.0` cut, the v1 milestone files start fresh at `m01-*.md`. The MILESTONE position in the version equals the file number, always.

| Phase | File | Release | Candidate milestone | Key scope |
|---|---|---|---|---|
| 0 | m01 | 1.1.0 | Cycle detection cap + schema v1 freeze | §3.1, §3.3, §3.4, §3.5 |
| 0 | m02 | 1.2.0 | Config purity + path-bounds helper | §3.4 |
| A | m03 | 1.3.0 | C/C++/Ruby/Kotlin adapters | §4.1 |
| A | m04 | 1.4.0 | Four new pattern categories | §4.2 |
| A | m05 | 1.5.0 | Fingerprint tier + partition stability + coupling decomposition | §4.3 |
| A | m06 | 1.6.0 | Generated code tagging | §4.4 |
| B | m07 | 1.7.0 | Hotspot ranking + attribution in `sdi diff` | §5.1, §5.2 |
| B | m08 | 1.8.0 | `sdi explain` | §5.3 |
| B | m09 | 1.9.0 | Rule-based hints | §5.4 |
| B | m10 | 1.10.0 | Canonical pinning | §5.5 |
| B | m11 | 1.11.0 | Aspirational split progress | §5.6 |
| B | m12 | 1.12.0 | Change coupling surfacing | §5.7 |
| C | m13 | 1.13.0 | Custom pattern category plugin system | §6.1 |
| C | m14 | 1.14.0 | Contract file parsing (OpenAPI, protobuf, GraphQL) | §6.2 |
| D | m15 | 1.15.0 | `sdi backfill` | §7.1 |
| D | m16 | 1.16.0 | GitHub Action v1 | §7.2 |
| D | m17 | 1.17.0 | `sdi diff` stdin + `sdi config` read-only + dynamic completions | §7.3, §7.4, §7.6 |
| D | m18 | 1.18.0 | Standalone binary distribution | §7.5 |

---

## Appendix B — Document Conventions

- "v0" refers to SDI 0.1.0 through 0.14.x (M1–M14 archived; the scaffold/prototype era).
- "v1" refers to SDI 1.x shipping from this document.
- "v2" refers to the post-v1 wave of companion surfaces (§13).
- **P1–P5** are v1's new principles (§2). **KD1–KD10** are v0 resolved design decisions; **KD11–KD20** are v1 additions (§15). **OQ1–OQ7** are v0 open questions resolved in §3.2; **OQ-v1-1** through **OQ-v1-6** are v1's new open questions (§14).
- Non-negotiable rules #1–#16 are from v0 (`.tekhton/DESIGN.md` and `CLAUDE.md`). v1 adds #17–#22 in §9.
- Phase numbering (0, A, B, C, D) is a planning convention for this document. Milestone files (`m01-*.md`, `m02-*.md`, …) are the work-unit convention; v1 milestone files start fresh after the `1.0.0` cut retires the v0 ones. The version's MILESTONE position equals the milestone file number, always.

---

*End of DESIGN_v1.md.*




