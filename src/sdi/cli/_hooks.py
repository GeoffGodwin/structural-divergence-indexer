"""Git hook script templates and installation utilities for SDI."""

from __future__ import annotations

import stat
from pathlib import Path

POST_MERGE_MARKER = "# SDI: post-merge hook"
PRE_PUSH_MARKER = "# SDI: pre-push hook"

# Runs snapshot after every merge on main/master; always exits 0.
_POST_MERGE_BODY = """\
# SDI: post-merge hook (installed by `sdi init`)
# Runs `sdi snapshot --quiet` after each merge. Always exits 0.
_sdi_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
case "$_sdi_branch" in
  main|master|develop) ;;
  *) exit 0 ;;
esac
sdi snapshot --quiet 2>/dev/null || true
"""

# Blocks push only when sdi check exits 10 (thresholds exceeded).
_PRE_PUSH_BODY = """\
# SDI: pre-push hook (installed by `sdi init`)
# Blocks push when drift thresholds are exceeded (sdi check exits 10).
sdi check
_sdi_exit=$?
if [ "$_sdi_exit" -eq 10 ]; then
  printf 'SDI: drift thresholds exceeded -- push blocked. Run: sdi check\\n' >&2
  exit 1
fi
exit 0
"""


def _make_executable(path: Path) -> None:
    """Add executable bits (u+x, g+x, o+x) to path."""
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_hook(
    hooks_dir: Path,
    hook_name: str,
    marker: str,
    script_body: str,
) -> str:
    """Install an SDI hook script into hooks_dir, non-destructively.

    If the hook file already contains marker, does nothing.
    If the hook file exists but lacks the marker, appends the script body.
    If the hook file does not exist, creates it with a #!/bin/sh shebang.

    Args:
        hooks_dir: Path to the .git/hooks/ directory.
        hook_name: Hook file name (e.g. "post-merge").
        marker: Unique string identifying this hook block.
        script_body: Shell script body to install (without shebang).

    Returns:
        One of: "installed", "appended", "already_present".
    """
    hook_path = hooks_dir / hook_name
    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if marker in existing:
            return "already_present"
        updated = existing.rstrip("\n") + "\n\n" + script_body
        # Direct write is intentional: .git/hooks/ is outside .sdi/, so the
        # atomic-write mandate (Critical System Rule 1) does not apply here.
        hook_path.write_text(updated, encoding="utf-8")
        _make_executable(hook_path)
        return "appended"

    # Direct write — same rationale as above (.git/hooks/ is not a .sdi/ path).
    hook_path.write_text("#!/bin/sh\n" + script_body, encoding="utf-8")
    _make_executable(hook_path)
    return "installed"


def install_post_merge_hook(hooks_dir: Path) -> str:
    """Install the SDI post-merge hook. Returns install status string."""
    return install_hook(hooks_dir, "post-merge", POST_MERGE_MARKER, _POST_MERGE_BODY)


def install_pre_push_hook(hooks_dir: Path) -> str:
    """Install the SDI pre-push hook. Returns install status string."""
    return install_hook(hooks_dir, "pre-push", PRE_PUSH_MARKER, _PRE_PUSH_BODY)
