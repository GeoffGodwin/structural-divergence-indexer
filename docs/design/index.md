# Design

SDI's design is documented across two living specifications:

- **[v0 (DESIGN.md)](v0.md)** — the original scaffold design that governed milestones M1 through M14. Closed for new work; the v0 era ends at SDI `0.14.x`.
- **[v1 (DESIGN_v1.md)](v1.md)** — the actionability era. Phases 0 (hardening), A (measurement depth), B (actionability), C (extensibility), D (operator ergonomics). Cuts at `1.0.0`.

A future `v2` design is seeded in DESIGN_v1.md §13 — companion surfaces (dashboard, gardener agent, cross-repo aggregation) — but is not yet authored.

## Core principles (carried across all designs)

- **Measurement over opinion.** Every claim decomposes to traceable inputs.
- **Fever chart, not thermometer.** Trends matter more than absolute values.
- **Automated inference, human ratification.** SDI proposes, humans ratify.
- **Safe defaults, zero mandatory config.**
- **Composable Unix tooling.** Local filesystem and git only; no daemon, no network.
- **Language-agnostic core, language-specific adapters.**
- **Deterministic and reproducible.**
- **Never classifies code as good or bad.**
- **Alert suppression is always time-boxed.**

The full set of non-negotiable rules is enumerated in each design document.

## Versioning

SDI uses **MAJOR.MILESTONE.PATCH** semantic versioning. See [Maintenance > Versioning](../maintenance/versioning.md) for the full policy.
