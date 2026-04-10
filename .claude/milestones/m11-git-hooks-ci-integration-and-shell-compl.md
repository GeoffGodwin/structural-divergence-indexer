### Milestone 11: Git Hooks, CI Integration, and Shell Completion

**Scope:** Implement git hook installation (post-merge for automatic snapshots, pre-push for drift gate), document CI integration patterns, add Click shell completion support, and handle signal interrupts cleanly.

**Deliverables:**
- Git hook installation in `src/sdi/cli/init_cmd.py`: offer to install post-merge and pre-push hooks during `sdi init`
- Post-merge hook script: checks branch, runs `sdi snapshot --quiet`, exits 0 always
- Pre-push hook script: runs `sdi check`, blocks push on exit 10
- Signal handlers (SIGINT, SIGTERM) for clean shutdown: discard incomplete snapshots, clean up tempfiles
- Click shell completion setup for bash, zsh, and fish
- `docs/ci-integration.md` with examples for GitHub Actions, GitLab CI, and generic CI
- `tests/integration/test_git_hooks.py`

**Acceptance criteria:**
- `sdi init` prompts to install post-merge and/or pre-push hooks
- Hook installation is non-destructive: appends to existing hooks or creates new ones
- Post-merge hook runs `sdi snapshot --quiet` and always exits 0 (never blocks merges)
- Pre-push hook runs `sdi check` and blocks push only on exit 10
- Ctrl+C during `sdi snapshot` discards the incomplete snapshot (no partial files on disk)
- Shell completion works for bash, zsh, and fish via Click's built-in mechanism
- `docs/ci-integration.md` contains working CI config examples

**Tests:**
- `tests/integration/test_git_hooks.py`: Hook installation creates executable hook files, post-merge hook runs snapshot on merge, pre-push hook blocks push when threshold exceeded, hook installation appends to existing hooks (does not overwrite), hook scripts are valid shell scripts (shellcheck if available)

**Watch For:**
- Git hooks must be executable (`chmod +x`) — this is easy to forget on Unix
- Existing hooks: if `.git/hooks/post-merge` already exists, the SDI hook script must be appended (or the user must be warned), not overwritten
- SIGINT handling: Python's default SIGINT raises `KeyboardInterrupt` — the top-level handler in `cli/__init__.py` should catch this and exit cleanly
- Pre-push hook blocking pushes is opt-in only — clearly document this and don't install it by default
- Shell completion scripts should be documented in README/help but not auto-installed (users add them to their shell profile)

**Seeds Forward:**
- Git hooks are the primary automated integration point — they drive the "run SDI on every merge" workflow
- CI integration documentation establishes the deployment pattern for SDI in real projects
- The post-v1 GitHub Actions marketplace action would wrap the patterns documented in `docs/ci-integration.md`

---
