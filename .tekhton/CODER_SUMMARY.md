# Coder Summary
## Status: COMPLETE

## What Was Implemented
- **`src/sdi/cli/_hooks.py`** (NEW): Git hook script templates (`POST_MERGE_MARKER`, `PRE_PUSH_MARKER`, `_POST_MERGE_BODY`, `_PRE_PUSH_BODY`) and installation utilities (`install_hook`, `install_post_merge_hook`, `install_pre_push_hook`). Non-destructive append: if the hook already contains the SDI marker it is a no-op; if it already exists without the marker, SDI block is appended; otherwise a new file with shebang is created. All hook files are made executable (u+x g+x o+x).
- **`src/sdi/cli/init_cmd.py`**: Added `--install-post-merge-hook` and `--install-pre-push-hook` CLI flags. Added `_maybe_install_hooks()` helper that also prompts via `click.confirm()` when running in a TTY and no hook flags are passed. Hook installation runs after the init sequence completes (or even when already initialized, without --force).
- **`src/sdi/cli/__init__.py`**: Registered SIGTERM handler (`_sigterm_handler`) at module load. Added `KeyboardInterrupt` catch in `_SDIGroup.invoke` that prints "Interrupted." and exits with code 1. Registered `completion_cmd`.
- **`src/sdi/cli/completion_cmd.py`** (NEW): `sdi completion <shell>` command for bash, zsh, and fish. Prints the eval line to stdout and a brief hint to stderr. Click's built-in completion mechanism handles the actual tab-completion via `_SDI_COMPLETE` env var.
- **`docs/ci-integration.md`** (NEW): Full CI integration guide with working examples for GitHub Actions (snapshot + drift gate), GitLab CI (snapshot + drift gate + allow_failure), and generic CI shell script. Includes git hooks, shell completion setup, threshold configuration, and exit code reference.
- **`tests/integration/test_git_hooks.py`** (NEW): 13 integration tests covering: executable file creation, shebang, marker presence, non-destructive append, idempotency, post-merge always-exits-0, post-merge skips non-main branches, pre-push blocks on exit 10, pre-push allows on exit 0, shellcheck syntax validation (skipped if shellcheck unavailable).

## Root Cause (bugs only)
N/A — feature implementation

## Files Modified
- `src/sdi/cli/_hooks.py` (NEW) — hook script templates and installation functions
- `src/sdi/cli/init_cmd.py` — added hook installation flags and `_maybe_install_hooks()` helper
- `src/sdi/cli/__init__.py` — SIGTERM handler, KeyboardInterrupt handling, completion_cmd registration
- `src/sdi/cli/completion_cmd.py` (NEW) — `sdi completion` shell completion helper
- `docs/ci-integration.md` (NEW) — CI integration documentation
- `tests/integration/test_git_hooks.py` (NEW) — 13 integration tests

## Human Notes Status
N/A — no human notes in this task

## Docs Updated
- `docs/ci-integration.md` (NEW) — created per milestone deliverable; documents git hooks, shell completion, GitHub Actions, GitLab CI, and generic CI integration patterns
