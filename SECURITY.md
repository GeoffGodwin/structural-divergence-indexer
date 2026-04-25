# Security Policy

## Reporting a Vulnerability

Please report suspected vulnerabilities **privately**. Do not open a public issue.

Preferred channel:

- **GitHub Security Advisories** — open a draft advisory at https://github.com/GeoffGodwin/structural-divergence-indexer/security/advisories/new

Alternate channel:

- Email **geoff.godwin@gmail.com** with subject `SDI security:` and a description of the issue. PGP is not currently offered.

Please include:

- A description of the issue and the impact you believe it has.
- Steps to reproduce, or a proof-of-concept if you have one.
- The SDI version (`sdi --version`), Python version, and OS.

Acknowledgement target: within 7 days. Fix or mitigation timeline depends on severity and is communicated in the advisory thread.

## Supported Versions

Only the **latest minor of the current MAJOR** receives security fixes. SDI uses MAJOR.MILESTONE.PATCH versioning (see `CLAUDE.md` "Version Naming" and `.tekhton/DESIGN_v1.md` §12.4); within a MAJOR, fixes land as PATCH releases against the latest MILESTONE.

| Version | Supported          |
| ------- | ------------------ |
| 0.14.x  | ✅                 |
| < 0.14  | ❌ (v0 era is closed for new MILESTONE work; older minors do not receive backports) |
| 1.x     | not yet released   |

When `1.0.0` cuts, the table updates to mark the latest 1.x minor as supported and 0.14.x as no longer supported. v0 will not be backported across the era boundary.

## Bug Bounty

There is no bug-bounty program. SDI is not yet published to PyPI and has no production user base; once it is, this policy will be revisited.

## Scope

In scope:

- The `sdi` Python package and its CLI, including release artifacts produced by `.github/workflows/release.yml`.
- The repository's CI workflows under `.github/workflows/`.

Out of scope:

- Findings against third-party dependencies (tree-sitter grammars, `igraph`, `leidenalg`, etc.) — please report those upstream. If a dependency vulnerability has a non-trivial impact on SDI users, an advisory note here is welcome.
- Test fixtures under `tests/fixtures/` — these contain intentionally-broken sample code that SDI parses but never executes.
