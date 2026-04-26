# Structural Divergence Indexer (SDI)

[![CI](https://github.com/GeoffGodwin/structural-divergence-indexer/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/GeoffGodwin/structural-divergence-indexer/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://geoffgodwin.github.io/structural-divergence-indexer/)
[![Latest release](https://img.shields.io/github/v/release/GeoffGodwin/structural-divergence-indexer?include_prereleases&sort=semver)](https://github.com/GeoffGodwin/structural-divergence-indexer/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

SDI is a CLI tool for measuring structural drift in a codebase over time.

It captures periodic snapshots, computes deltas, and helps teams answer:
- Is structural divergence accelerating?
- Which dimensions are getting worse?
- What should we fix first to bring drift back down?

SDI tracks four dimensions per snapshot:
- `pattern_entropy`
- `convention_drift`
- `coupling_topology`
- `boundary_violations`

Pattern entropy and convention drift are reported globally and per-language. Categories declare which languages they apply to; non-applicable languages contribute zero. A 95%-shell repo's `error_handling` entropy under `pattern_entropy_by_language["shell"]` reflects shell-specific shapes only. For example, `class_hierarchy` is Python/JS/TS/Java only — a shell file's class-like structure does not pollute the Python entropy count, and a Python-only project will never see an empty `class_hierarchy` entry under a non-Python key.

## Why SDI

- Deterministic and local: no network calls during analysis.
- Fast to adopt: initialize in a repo and run one command to capture baseline.
- Trend-first: you get time series output, not only one-off checks.
- CI and hooks friendly: clear exit codes and scriptable outputs.

## 60-Second Quick Start

Run these in the target repository you want to analyze.

```bash
# 1) Install with full language support
pip install "sdi[all]"

# 2) Initialize SDI in the repo
sdi init --install-post-merge-hook

# 3) Capture baseline snapshot
sdi snapshot

# 4) Inspect latest snapshot and trend
sdi show
sdi trend --last 10
```

What this creates:
- `.sdi/config.toml`
- `.sdi/snapshots/`
- `.sdi/cache/` entry in `.gitignore`

## Developer Workflow (Daily Use)

```bash
# Capture a new point in time
sdi snapshot

# Compare latest two snapshots
sdi diff

# Threshold gate (exit 10 if exceeded)
sdi check

# Inspect shape-level hotspots
sdi catalog

# Longitudinal trend
sdi trend --last 20
```

## Hooking into Git

### Built-in hooks via `sdi init`

- `--install-post-merge-hook`
- Runs `sdi snapshot --quiet` after merges on `main`, `master`, or `develop`.
- Never blocks the merge.

- `--install-pre-push-hook`
- Runs `sdi check` before push.
- Blocks push only when thresholds are exceeded (`sdi check` exits `10`).

Example:

```bash
sdi init --install-post-merge-hook --install-pre-push-hook
```

### Optional: rerun on every commit

SDI currently ships post-merge and pre-push installers. If you want per-commit capture + diff, add a `post-commit` hook in your target repository:

```sh
#!/bin/sh
# .git/hooks/post-commit

# keep local commits fast; skip on non-main branches if desired
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
case "$branch" in
  main|master|develop) ;;
  *) exit 0 ;;
esac

sdi snapshot --quiet >/dev/null 2>&1 || exit 0

# Diff only when at least two snapshots exist
count=$(ls .sdi/snapshots/*.json 2>/dev/null | wc -l)
if [ "$count" -ge 2 ]; then
  sdi diff || true
fi

exit 0
```

Then make it executable:

```bash
chmod +x .git/hooks/post-commit
```

## CI Gate Pattern

Minimal pipeline pattern:

```bash
pip install "sdi[all]"
sdi snapshot
sdi check
```

Interpretation:
- exit `0`: within thresholds
- exit `10`: threshold exceeded (treat as gate fail or warning based on policy)

See `docs/ci-integration.md` for GitHub Actions, GitLab, and generic shell patterns.

## Bringing the Score Back Down (Actionable Loop)

SDI does not collapse everything into a single opaque score. Instead, fix by dimension with an evidence-driven loop:

1. Capture and detect: `sdi snapshot`, `sdi check`.
2. Identify changed dimensions: `sdi diff`.
3. Find structural hotspots: `sdi catalog` (look for high `velocity` and `spread` shapes).
4. Validate boundaries: `sdi boundaries --propose` then ratify/edit with `sdi boundaries --ratify`.
5. Refactor targeted modules, then snapshot again.
6. Confirm trendline improvement: `sdi trend --last 10`.

A practical interpretation:
- Rising `pattern_entropy_delta` suggests too many competing structural shapes.
- Rising `convention_drift_delta` suggests conventions are fragmenting.
- Rising `coupling_topology_delta` suggests dependency structure is becoming denser or less modular.
- Rising `boundary_violations_delta` suggests increasing cross-boundary leakage.

## Language Support

SDI supports Python, TypeScript, JavaScript, Go, Java, and Rust out of the box with `pip install sdi`. Full language support including shell is installed with `pip install 'sdi[all]'`.

### Shell

**Supported extensions:** `.sh`, `.bash`, `.zsh`, `.ksh`, `.dash`, `.ash`. Note: `.fish` is not supported (fish syntax is not parsed by the underlying tree-sitter-bash grammar).

**Shebang detection:** Extensionless executable files with a recognized bash/sh/zsh shebang line (e.g. `#!/usr/bin/env bash`, `#!/bin/sh`) are automatically included in analysis without requiring a file extension.

**Installation:** `pip install 'sdi[all]'` installs `tree-sitter-bash` and enables shell analysis. Without it, shell files are skipped with a per-file warning.

**Categories detected for shell:**
- `error_handling` — `set -e`/`-u`/`-o pipefail` invocations, `trap` handlers (ERR, EXIT, INT, TERM, HUP, QUIT), `exit`/`return` non-zero, `cmd || exit` list-bail patterns, `if_statement` bodies with exit/return, test expressions containing command substitutions.
- `logging` — `echo`, `printf`, `logger`, `tee` commands; `>&2` stderr redirect forms (tracked as a distinct shape from stdout logging).
- `data_access` — Commands from a fixed allow-list: `curl`, `wget`, `jq`, `yq`, `psql`, `mysql`, `mysqldump`, `pg_dump`, `redis-cli`, `mongo`, `mongosh`, `sqlite3`, `aws`, `gcloud`, `kubectl`, `az`, `doctl`, `terraform`.
- `async_patterns` — Background jobs (`cmd &`), `wait`, wide pipelines (3+ stages), `xargs`/`parallel` with `-P`/`--max-procs`.

**Known limits:**
- Dynamic `source` paths (e.g. `source "$DIR/lib.sh"`) are silently skipped; only static literals are resolved to repo-relative paths.
- Heredoc bodies are not pattern-matched.
- Fish syntax is not supported.
- Parse failures emit a per-file warning and skip the file; analysis continues with available files.
- Generated shell wrappers (e.g. autotools scripts, codegen output) can inflate entropy. Add such directories to `[core] exclude` in `.sdi/config.toml`.

## Configuration

`sdi init` writes `.sdi/config.toml` with defaults and comments. Common edits:

```toml
[thresholds]
pattern_entropy_rate = 2.0
convention_drift_rate = 0.10
coupling_delta_rate = 0.15
boundary_violation_rate = 5.0

# Time-boxed migration intent (required: expires)
[thresholds.overrides.error_handling]
pattern_entropy_rate = 5.0
expires = "2026-09-30"
reason = "Result-type migration"
```

Notes:
- Threshold overrides without `expires` are rejected.
- Expired overrides are ignored automatically.

## Command Cheat Sheet

```bash
sdi init
sdi snapshot
sdi show [snapshot_ref]
sdi diff [snapshot_a] [snapshot_b]
sdi trend --last 20
sdi check [snapshot_ref]
sdi catalog [snapshot_ref]
sdi boundaries [--propose|--ratify|--export path]
sdi completion [bash|zsh|fish]
```

## Output and Exit Codes

- `stdout`: data output (`text`, `json`, `csv`)
- `stderr`: progress/log output

Exit codes:
- `0` success
- `1` runtime error
- `2` config/environment error
- `3` analysis error
- `10` threshold exceeded (`sdi check` only)

## Local Development (This Repository)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,all]"
pre-commit install --hook-type pre-push

pytest
ruff check src/ tests/
mypy src/sdi/
```

## License

MIT
