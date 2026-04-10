### Milestone 8: CI Gate (`sdi check`) and Git Hook Integration

**Scope:** Implement the `sdi check` command — the CI-friendly gate that exits non-zero when drift exceeds thresholds. Implement per-category threshold overrides with expiry dates. Implement git hook installation (post-merge and pre-push). This milestone makes SDI usable in real CI pipelines.

**Deliverables:**
- `sdi check` command: captures snapshot (or uses provided), computes drift rates against history, exits 10 if threshold exceeded
- Per-category threshold override handling: reads `[thresholds.overrides.*]` from config, respects expiry dates, falls back to defaults when expired
- Threshold comparison logic: per-dimension rate comparison against configured thresholds
- Detailed threshold breach reporting: which dimensions exceeded, by how much, current vs threshold values
- Git hook installation: `sdi init` offers post-merge hook, optional pre-push hook
- Hook scripts: thin shell wrappers that check branch and run `sdi snapshot` or `sdi check`
- Post-merge hook: runs `sdi snapshot --quiet`, always exits 0 (never blocks merges)
- Pre-push hook: runs `sdi check`, exits non-zero to block pushes exceeding thresholds
- Hook installation is non-destructive: appends to existing hooks

**Files to create or modify:**
- `src/sdi/cli/check_cmd.py`
- `src/sdi/snapshot/delta.py` (extend with threshold comparison)
- `src/sdi/config.py` (extend with threshold override parsing + expiry logic)
- `src/sdi/cli/init_cmd.py` (extend with hook installation)
- `tests/unit/test_check.py`
- `tests/integration/test_git_hooks.py`
- `docs/ci-integration.md`

**Acceptance criteria:**
- `sdi check` with all dimensions within threshold exits 0
- `sdi check` with one or more dimensions exceeding threshold exits 10
- Exit 10 output names each exceeded dimension with current rate and threshold
- `sdi check --threshold 0.5` overrides all dimension thresholds
- `sdi check --dimension boundary_violations` checks only one dimension
- `sdi check --snapshot path.json` uses existing snapshot instead of capturing new
- Per-category threshold override in config increases allowed rate for the specified category
- Expired overrides are silently ignored — defaults resume
- Override without `expires` field produces exit code 2
- `sdi init` prompts about post-merge hook installation
- Post-merge hook runs `sdi snapshot --quiet` and exits 0 regardless of snapshot outcome
- Pre-push hook runs `sdi check` and passes through the exit code
- Hooks are appended to existing hook files, not overwritten
- Hooks include `#!/bin/sh` shebang and are marked executable
- `docs/ci-integration.md` documents: generic CI setup, GitHub Actions example, GitLab CI example, Jenkins example

**Tests:**
- `tests/unit/test_check.py`:
  - All dimensions below threshold → exit 0
  - One dimension above threshold → exit 10 with dimension named
  - Multiple dimensions above threshold → exit 10 with all named
  - CLI `--threshold` overrides config threshold
  - `--dimension` flag limits check to specified dimension
  - Per-category override with future expiry date increases allowed threshold
  - Per-category override with past expiry date is ignored (defaults apply)
  - Override without `expires` field → exit code 2
  - No previous snapshots → exit 0 (baseline, nothing to compare)
- `tests/integration/test_git_hooks.py`:
  - Post-merge hook is installed and executable
  - Pre-push hook is installed and executable
  - Existing hook content is preserved when appending
  - Hook runs `sdi snapshot`/`sdi check` correctly

**Watch For:**
- Threshold comparison must use rates (deltas per interval), not absolute values. A codebase with high-but-stable entropy should not trigger `sdi check`.
- When there are fewer than 2 snapshots, `sdi check` has no rate to compute. Exit 0 with a message like "insufficient history for drift rate computation."
- Per-category threshold overrides affect only the specified dimension within the specified category — not global thresholds.
- Expiry date comparison must use UTC. Parse ISO 8601 dates and compare against `datetime.now(UTC)`.
- Git hooks must handle the case where `sdi` is not in PATH (installed in a virtualenv). Include a comment in the hook about activating the venv if needed.
- The `docs/ci-integration.md` file should show real, copy-pasteable CI configuration snippets.

**Seeds Forward:**
- `sdi check` exit codes are used by CI systems and git hooks. The exit code semantics are now a public API.
- The CI integration guide is the primary user-facing documentation for v1 adoption.
- Hook installation patterns established here may be extended in the future for other hook types.

---
