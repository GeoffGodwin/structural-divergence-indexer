# CLI Reference

SDI exposes a small set of verbs. Run any with `--help` for the full flag list.

## `sdi init`

One-time setup in a target repository. Creates `.sdi/config.toml` with safe defaults. Idempotent — re-running does not overwrite an existing config.

## `sdi snapshot`

Capture a structural fingerprint of the current working tree. Writes a JSON snapshot to `.sdi/snapshots/`. Honors `[snapshots.retention]` — oldest snapshots are pruned synchronously after write.

```bash
sdi snapshot                          # current working tree
sdi snapshot --commit HEAD~5          # snapshot at a historical commit
sdi snapshot --paths src/billing/     # scope to a subtree
```

## `sdi show`

Print a human-readable summary of the latest snapshot (or a specified one).

```bash
sdi show                              # latest
sdi show --format json                # machine-readable
sdi show <snapshot-file>              # specific snapshot
```

## `sdi diff`

Compute the delta between two snapshots.

```bash
sdi diff <old> <new>
sdi diff HEAD~1 HEAD                  # convenience: implicit snapshots at refs
```

## `sdi trend`

Trend analysis across the snapshot retention window.

```bash
sdi trend
sdi trend --since 2026-01-01
sdi trend --format json | jq
```

## `sdi check`

Threshold gate. Exits 10 if any drift rate exceeds its declared threshold.

```bash
sdi check
sdi check --format json
```

Use `[thresholds.overrides.<category>]` in config to declare migration intent with an explicit `expires` date. Without an expiry, override is a config error (exit 2).

## `sdi catalog`

List pattern shapes grouped by category, with instance counts and locations.

```bash
sdi catalog
sdi catalog --category error_handling
```

## `sdi boundaries`

Manage the boundary specification.

```bash
sdi boundaries --review               # show inferred vs declared
sdi boundaries --suggest              # propose updates to .sdi/boundaries.yaml
```

## Output streams

- **stdout** is reserved for requested data (summaries, JSON, CSV).
- **stderr** carries logs, progress bars, and warnings.

This means `sdi show --format json | jq '.'` always works.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime error |
| 2 | Config or environment error |
| 3 | Analysis error |
| 10 | Threshold exceeded (`sdi check` only) |

Exit codes are a stable public API — they do not change across versions.

## Environment variables

| Variable | Effect |
|---|---|
| `SDI_CONFIG_PATH` | Override config file location |
| `SDI_SNAPSHOT_DIR` | Override snapshot storage directory |
| `SDI_LOG_LEVEL` | Log verbosity (`DEBUG`, `INFO`, `WARN`, `ERROR`) |
| `SDI_WORKERS` | Parallel worker count for parsing |
| `NO_COLOR` | Disable colored output (no-color.org standard) |
