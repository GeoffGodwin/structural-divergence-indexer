# Versioning

SDI uses **MAJOR.MILESTONE.PATCH** semantic versioning. Each position maps to a unit of work the project produces.

## The three positions

- **MAJOR** — the design era. Increments when a new DESIGN document is ratified. Each cross-era release is a MAJOR bump because the design contract changed.
- **MILESTONE** — the position of the milestone within the current MAJOR. `1` for the first milestone shipped in the era, `2` for the second, and so on. **The counter starts over at every MAJOR bump.** Versions within a MAJOR are dense (no gaps).
- **PATCH** — a bugfix, drift fix, or ad-hoc / human-note correction against a shipped milestone. Resets to 0 on every new MILESTONE.

Milestone files under `.claude/milestones/` (`m01-*.md`, `m02-*.md`, …) follow the same per-era numbering. At each MAJOR cut, the previous era's milestone files are retired (archived in `MILESTONE_ARCHIVE.md`) and the new era starts fresh at `m01-*.md`. The MILESTONE position in the version equals the milestone file number, always.

## Era boundaries

| Era | Versions | Design | Status |
|---|---|---|---|
| v0 | `0.1.0`–`0.14.x` | `.tekhton/DESIGN.md` | 14 milestones shipped; files retired at the `1.0.0` cut |
| v1 | `1.0.0`, `1.1.0`, `1.2.0`, … | `.tekhton/DESIGN_v1.md` | First v1 milestone is the new `m01-*.md` → `1.1.0`; cuts `1.0.0` at end of the lifecycle PR |
| v2 | `2.0.0`+ | future | DESIGN_v2.md not yet authored |

Within a MAJOR there are no gaps — `1.0.0` is followed by `1.1.0`, then `1.2.0`, `1.3.0`, and so on. The MILESTONE counter resets on the next MAJOR bump (the first v2 milestone is `2.1.0`).

## Cut criteria

A version is cut when the work behind its position is complete and validated:

- **MAJOR cut (`X.0.0`)** — DESIGN_vX is ratified. The CI/CD/docs/release-pipeline lifecycle work for the new era has landed. No milestones under the new design have shipped yet; the cut is a checkpoint.
- **MILESTONE cut (`X.M.0`)** — Milestone M's acceptance criteria are met, tests pass on CI, CHANGELOG entry written.
- **PATCH cut (`X.M.P`)** — One or more bugfixes, drift fixes, or human-note corrections have landed since the last MILESTONE cut.

## Where the version lives

The version is single-sourced in `pyproject.toml`:

```toml
[project]
version = "0.14.0"
```

`src/sdi/__init__.py` reads from package metadata via `importlib.metadata` — it never carries a hardcoded version string. This eliminates drift.

Tekhton's `.claude/project_version.cfg` mirrors the version for tooling that doesn't run inside Python. Its `VERSION_FILES` declaration lists only `pyproject.toml`.

## Backward compatibility within a MAJOR

Within the same MAJOR (e.g., across all 1.x releases):

- Snapshot schema is additive-only.
- CLI verbs are never removed. New verbs land additively.
- CLI flags are never removed within a MAJOR; flags may be deprecated with a warning for one MILESTONE before removal in the next MAJOR.
- Exit codes are stable from v0 onward — cross-era stable.
- Config keys are never repurposed.

A breaking change to any of the above requires a MAJOR bump. Because MAJOR ties to a new DESIGN document, breaking changes are deliberate, documented, and infrequent.

## See also

- [Release Process](releases.md) — the mechanical pipeline.
- [DESIGN_v1.md §12](../design/v1.md) — the full versioning policy spec.
