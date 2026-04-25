# Milestones

SDI work is organized into milestones, numbered per design era. Each milestone has a file under `.claude/milestones/` (`m01-*.md`, `m02-*.md`, …) and ships as a release `X.M.0` where `X` is the design era and `M` is the milestone number. The numbering resets at each new design era; the previous era's milestone files are retired into `MILESTONE_ARCHIVE.md` at the MAJOR cut. See [Versioning](maintenance/versioning.md) for the full policy.

## v0 era (M1–M14, shipped)

The original scaffold design. All shipped; final v0 release is `0.14.x`.

| # | Milestone | Released in |
|---|---|---|
| M1 | Project Skeleton, Config System, and Core Data Structures | 0.1.0 |
| M2 | File Discovery and Tree-Sitter Parsing | 0.1.0 |
| M3 | Additional Language Adapters | 0.1.0 |
| M4 | Dependency Graph Construction and Metrics | 0.1.0 |
| M5 | Leiden Community Detection and Partition Stability | 0.1.0 |
| M6 | Pattern Fingerprinting and Catalog | 0.1.0 |
| M7 | Snapshot Assembly, Delta Computation, and Trend Analysis | 0.1.0 |
| M8 | CLI Commands — snapshot, show, diff, trend, check, catalog | 0.1.1–0.1.2 |
| M9 | Boundary Specification and Intent Divergence | 0.1.3 |
| M10 | Caching and Performance Optimization | 0.1.4 |
| M11 | Git Hooks, CI Integration, and Shell Completion | 0.1.5 |
| M12 | Integration Tests, Polish, and Packaging | 0.1.6–0.1.7 |
| M13 | Shell Language Discovery and Adapter Foundation | 0.1.8 |
| M14 | Shell Pattern Quality, Trend Calibration, and Rollout | 0.1.9 |

The mapping above reflects the historical patch-only versioning that pre-dated the MAJOR.MILESTONE.PATCH switch. From `0.14.0` forward, each milestone occupies its own MILESTONE position.

## v1 era (planned)

Seeded in DESIGN_v1.md Appendix A. See the [v1 design](design/v1.md) for the full phase plan.

After the `1.0.0` cut, v1 milestone files start fresh at `m01-*.md`.

| Phase | Files | Releases |
|---|---|---|
| Phase 0 — v0 Hardening | m01, m02 | 1.1.0, 1.2.0 |
| Phase A — Measurement Depth | m03, m04, m05, m06 | 1.3.0 – 1.6.0 |
| Phase B — Actionability | m07, m08, m09, m10, m11, m12 | 1.7.0 – 1.12.0 |
| Phase C — Extensibility | m13, m14 | 1.13.0, 1.14.0 |
| Phase D — Operator Ergonomics | m15, m16, m17, m18 | 1.15.0 – 1.18.0 |

Milestone authoring is handled by Tekhton; the seed list above is non-binding.
