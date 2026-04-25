# Quick Start

The fastest path from zero to a useful snapshot.

## Install

SDI is not yet published to PyPI (battle-test phase — see the [Maintenance > Release Process](maintenance/releases.md) page). Install from source:

```bash
git clone https://github.com/GeoffGodwin/structural-divergence-indexer.git
cd structural-divergence-indexer
pip install -e ".[all]"
```

`[all]` brings in the tree-sitter grammars and Leiden detection dependencies. Without it, you get the core CLI but no language adapters or community detection.

## Capture a snapshot

In any git repository:

```bash
sdi init       # one-time: creates .sdi/config.toml with safe defaults
sdi snapshot   # captures structural fingerprint into .sdi/snapshots/
sdi show       # prints the latest snapshot's summary
```

That's the whole loop. Repeat `sdi snapshot` over time (a pre-merge hook, a nightly job, a manual rerun) and your `.sdi/snapshots/` directory becomes a fever chart of structural drift.

## Compare two snapshots

```bash
sdi diff <old> <new>      # delta between two snapshots
sdi trend                 # rate-of-change across the snapshot window
sdi catalog               # pattern shapes grouped by category
```

## Gate a CI build

```bash
sdi check    # exits 10 if any threshold is exceeded
```

See [CI Integration](ci-integration.md) for full pipeline wiring.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime error |
| 2 | Config or environment error |
| 3 | Analysis error |
| 10 | Threshold exceeded (`sdi check` only) |

These are stable across all versions, including pre-1.0.
