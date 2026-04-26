# CI Integration Guide

SDI integrates with any CI system that can run Python packages. The canonical pattern is:

```
pip install sdi
sdi snapshot        # capture a structural snapshot
sdi check           # exit 10 if thresholds exceeded, 0 otherwise
```

`sdi check` exits 0 on success and 10 when one or more drift thresholds are exceeded.
Use exit code 10 (not non-zero in general) when writing conditional logic.

---

## GitHub Actions

### Snapshot on every push to main

```yaml
# .github/workflows/sdi-snapshot.yml
name: SDI Snapshot

on:
  push:
    branches: [main, master]

jobs:
  snapshot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history for trend analysis

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install SDI
        run: pip install sdi

      - name: Capture snapshot
        run: sdi snapshot

      - name: Upload snapshots artifact
        uses: actions/upload-artifact@v4
        with:
          name: sdi-snapshots
          path: .sdi/snapshots/
          retention-days: 90
```

### Drift gate on pull requests

```yaml
# .github/workflows/sdi-check.yml
name: SDI Drift Gate

on:
  pull_request:
    branches: [main, master]

jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install SDI
        run: pip install sdi

      - name: Download snapshots artifact
        uses: actions/dawidownload-artifact@v4
        continue-on-error: true   # first run has no prior snapshots
        with:
          name: sdi-snapshots
          path: .sdi/snapshots/

      - name: Capture snapshot
        run: sdi snapshot

      - name: Check drift thresholds
        run: |
          sdi check
          exit_code=$?
          if [ $exit_code -eq 10 ]; then
            echo "::error::SDI drift thresholds exceeded. Run 'sdi check' locally for details."
            exit 1
          fi
```

### Combined snapshot + check (single workflow)

```yaml
# .github/workflows/sdi.yml
name: SDI

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  sdi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install sdi
      - run: sdi snapshot
      - run: sdi check || { [ $? -eq 10 ] && echo "Thresholds exceeded" && exit 1; }
```

---

## GitLab CI

### Snapshot job

```yaml
# .gitlab-ci.yml
stages:
  - analysis

sdi-snapshot:
  stage: analysis
  image: python:3.11-slim
  before_script:
    - pip install sdi
  script:
    - sdi snapshot
  artifacts:
    paths:
      - .sdi/snapshots/
    expire_in: 90 days
  only:
    - main
    - master
```

### Drift gate job

```yaml
sdi-check:
  stage: analysis
  image: python:3.11-slim
  before_script:
    - pip install sdi
  script:
    - sdi snapshot
    - |
      sdi check
      sdi_exit=$?
      if [ $sdi_exit -eq 10 ]; then
        echo "SDI: drift thresholds exceeded."
        exit 1
      fi
  except:
    - main
    - master
```

### Full example with cache restore

```yaml
sdi:
  stage: analysis
  image: python:3.11-slim
  cache:
    key: sdi-snapshots
    paths:
      - .sdi/snapshots/
  before_script:
    - pip install sdi
  script:
    - sdi snapshot
    - sdi check
  allow_failure:
    exit_codes: 10   # report threshold breach without blocking pipeline
```

> **Note:** `allow_failure.exit_codes` requires GitLab 13.8+. Without it, use
> `sdi check || [ $? -eq 10 ]` to treat exit 10 as a warning rather than a failure.

---

## Generic CI / Shell Script

For Jenkins, Buildkite, CircleCI, or any system that runs shell commands:

```bash
#!/bin/sh
# sdi-ci.sh — run in your CI pipeline

set -e

pip install sdi

# Capture structural snapshot
sdi snapshot

# Check thresholds — exit 10 means drift exceeded, 0 means OK
sdi check
sdi_exit=$?

if [ "$sdi_exit" -eq 10 ]; then
  echo "SDI: drift thresholds exceeded. Review with 'sdi trend' and 'sdi check'."
  exit 1
fi

echo "SDI: all dimensions within thresholds."
```

### Trend report (optional)

```bash
# Print last 10 snapshots as a trend table
sdi trend --limit 10

# Output trend as JSON for downstream processing
sdi trend --format json | jq '.snapshots[-1]'
```

---

## Git Hooks (local enforcement)

SDI can install git hooks to enforce snapshots and drift checks locally.

### Post-merge hook (automatic snapshots)

Run `sdi init --install-post-merge-hook` to install a hook that automatically
captures a snapshot after each merge on `main`, `master`, or `develop`.
The hook always exits 0 — it never blocks a merge.

### Pre-push hook (opt-in drift gate)

Run `sdi init --install-pre-push-hook` to install a hook that runs `sdi check`
before every push. If thresholds are exceeded (exit 10), the push is blocked.
**This is opt-in** — do not install it unless your team has agreed on thresholds.

### Shell completion

Enable tab completion for `sdi` subcommands and flags:

```bash
# bash — add to ~/.bashrc
eval "$(sdi completion bash)"

# zsh — add to ~/.zshrc
eval "$(sdi completion zsh)"

# fish — add to ~/.config/fish/completions/sdi.fish
sdi completion fish | source
```

---

## Threshold Configuration

Thresholds are configured in `.sdi/config.toml`. The defaults are conservative:

```toml
[thresholds]
pattern_entropy_rate = 2.0
convention_drift_rate = 0.10
coupling_delta_rate = 0.15
boundary_violation_rate = 5.0
```

To declare a migration window (suppresses a threshold temporarily):

```toml
[thresholds.overrides.error_handling]
pattern_entropy_rate = 5.0
expires = "2026-09-30"
reason = "Migrating to Result types per ADR-0047"
```

Overrides without an `expires` date are rejected with exit code 2.

---

## Excluding Test Directories from the Pattern Catalog

Test directories often contain intentionally varied code — each test file may use a different
error-handling style, data-access pattern, or control structure by design. Including them in
`pattern_entropy` and `convention_drift` inflates structural-shape counts without representing
real codebase drift. Use `patterns.scope_exclude` to filter them out of Stage 4 (pattern catalog)
while keeping them in the dependency graph and community partition.

```toml
[patterns]
scope_exclude = [
  "tests/**",
  "test/**",
  "**/__tests__/**",
  "**/*.test.ts",
  "**/*.spec.ts",
]
```

**Important:** Files matched by `scope_exclude` are still included in the dependency graph,
the community partition, and boundary spread calculations. Coupling and boundary metrics still
reflect the relationship between test files and application code — only the pattern-shape
signal is suppressed for the excluded paths.

When files are excluded, `sdi show` prints an informational note:

```
Pattern catalog excluded 12 file(s) via patterns.scope_exclude.
```

This note also appears in the snapshot JSON as `pattern_catalog.meta.scope_excluded_file_count`.
Use this field in downstream tooling to detect misconfigured or unexpectedly large exclusion sets.

---

## Shell-Heavy Repositories

Default thresholds are tuned for application code (Python, TypeScript, Go, etc.). Shell-script-heavy repositories (ops tooling, CI scripts, deploy pipelines) often have higher shape diversity by nature; the default `pattern_entropy_rate = 2.0` and `convention_drift_rate = 0.10` may fire more frequently than intended.

### Worked example: running `sdi check` against a shell-heavy repo

```bash
# Install with shell grammar support
pip install 'sdi[all]'

# Initialize and capture baseline
cd /path/to/my-ops-repo
sdi init
sdi snapshot

# After adding new shell scripts (e.g. deploy/health-check.sh with xargs -P):
sdi snapshot
sdi check   # may exit 10 if new shapes exceed pattern_entropy_rate = 2.0
sdi diff    # shows which dimensions changed and by how much
```

If `sdi check` exits 10 after expected script additions, use a time-boxed override instead of lowering the global thresholds.

### TOML override for shell-script-heavy repos

Add to `.sdi/config.toml` while migrating ops scripts:

```toml
[thresholds.overrides.error_handling]
pattern_entropy_rate = 6.0
expires = "2026-Q4"
reason = "Migrating ops scripts from set -e to explicit error traps"

[thresholds.overrides.async_patterns]
pattern_entropy_rate = 5.0
expires = "2026-12-31"
reason = "Pipeline parallelism rollout in deploy/"
```

> **Note:** Overrides without an `expires` date are rejected with exit code 2.
> Expired overrides are silently ignored — default thresholds resume automatically.

The override mechanism is the supported relief valve. Default thresholds are not lowered globally to accommodate script-heavy repos.

---

## Exit Code Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error |
| 2 | Config or environment error |
| 3 | Analysis error (e.g. no parseable files) |
| 10 | Drift threshold exceeded (`sdi check` only) |

Use `[ $? -eq 10 ]` to distinguish threshold breach from other errors.
