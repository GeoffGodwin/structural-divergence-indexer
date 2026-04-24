"""Integration tests for git hook installation and execution.

Covers:
- Hook file creation and permissions
- Non-destructive append to existing hooks
- Post-merge hook always exits 0
- Pre-push hook blocks on sdi check exit 10
- Shell script validity (shellcheck if available)
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdi.cli._hooks import POST_MERGE_MARKER, PRE_PUSH_MARKER
from tests.conftest import run_sdi


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bare_git_repo(tmp_path: Path) -> Path:
    """A minimal git-like repo with no SDI initialization."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hooks").mkdir()
    return tmp_path


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Hook file creation and permissions
# ---------------------------------------------------------------------------


def test_post_merge_hook_creates_executable_file(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    result = run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    assert result.exit_code == 0, result.output

    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    assert hook.exists(), "post-merge hook file was not created"
    assert hook.stat().st_mode & stat.S_IXUSR, "post-merge hook is not executable"


def test_pre_push_hook_creates_executable_file(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    result = run_sdi(cli_runner, ["init", "--install-pre-push-hook"], bare_git_repo)
    assert result.exit_code == 0, result.output

    hook = bare_git_repo / ".git" / "hooks" / "pre-push"
    assert hook.exists(), "pre-push hook file was not created"
    assert hook.stat().st_mode & stat.S_IXUSR, "pre-push hook is not executable"


def test_post_merge_hook_has_shebang(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    content = hook.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/sh"), "hook must start with #!/bin/sh"


def test_post_merge_hook_contains_marker(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    assert POST_MERGE_MARKER in hook.read_text(encoding="utf-8")


def test_pre_push_hook_contains_marker(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    run_sdi(cli_runner, ["init", "--install-pre-push-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "pre-push"
    assert PRE_PUSH_MARKER in hook.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Non-destructive append
# ---------------------------------------------------------------------------


def test_install_appends_to_existing_hook(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    hook.write_text("#!/bin/sh\n# pre-existing hook\necho existing\n", encoding="utf-8")
    hook.chmod(0o755)

    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)

    content = hook.read_text(encoding="utf-8")
    assert "pre-existing hook" in content, "existing hook content was lost"
    assert POST_MERGE_MARKER in content, "SDI block was not appended"


def test_install_does_not_duplicate_existing_block(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    """Running init twice must not duplicate the SDI hook block."""
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    run_sdi(cli_runner, ["init", "--force", "--install-post-merge-hook"], bare_git_repo)

    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    content = hook.read_text(encoding="utf-8")
    assert content.count(POST_MERGE_MARKER) == 1, "SDI block was duplicated"


# ---------------------------------------------------------------------------
# Post-merge hook execution behaviour
# ---------------------------------------------------------------------------


def _fake_sdi(bin_dir: Path, exit_code: int) -> Path:
    """Write a fake `sdi` script that exits with the given code."""
    script = bin_dir / "sdi"
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_post_merge_hook_always_exits_zero(
    tmp_path: Path, bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    """Post-merge hook must exit 0 even when sdi snapshot fails."""
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_sdi(bin_dir, exit_code=1)  # sdi fails

    # Fake git to return "main" so branch check passes
    fake_git = bin_dir / "git"
    fake_git.write_text("#!/bin/sh\necho main\n", encoding="utf-8")
    fake_git.chmod(0o755)

    env = {**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", "")}
    result = subprocess.run(
        [str(hook)],
        env=env,
        capture_output=True,
        cwd=str(bare_git_repo),
    )
    assert result.returncode == 0, "post-merge hook must always exit 0"


def test_post_merge_hook_skips_non_main_branches(
    tmp_path: Path, bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    """Post-merge hook must exit 0 and skip snapshot on feature branches."""
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # Fake git returns a feature branch name
    fake_git = bin_dir / "git"
    fake_git.write_text("#!/bin/sh\necho feature/my-feature\n", encoding="utf-8")
    fake_git.chmod(0o755)

    # sdi would fail if called — but it should not be called on a feature branch
    invocation_log = tmp_path / "sdi_called"
    fake_sdi = bin_dir / "sdi"
    fake_sdi.write_text(
        f"#!/bin/sh\ntouch {invocation_log}\nexit 0\n", encoding="utf-8"
    )
    fake_sdi.chmod(0o755)

    env = {**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", "")}
    result = subprocess.run(
        [str(hook)],
        env=env,
        capture_output=True,
        cwd=str(bare_git_repo),
    )
    assert result.returncode == 0
    assert not invocation_log.exists(), "sdi should not be called on feature branches"


# ---------------------------------------------------------------------------
# Pre-push hook execution behaviour
# ---------------------------------------------------------------------------


def test_pre_push_hook_blocks_on_exit_10(
    tmp_path: Path, bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    """Pre-push hook must block (exit non-zero) when sdi check exits 10."""
    run_sdi(cli_runner, ["init", "--install-pre-push-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "pre-push"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_sdi(bin_dir, exit_code=10)

    env = {**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", "")}
    result = subprocess.run(
        [str(hook)],
        env=env,
        capture_output=True,
        cwd=str(bare_git_repo),
    )
    assert result.returncode != 0, "pre-push hook must block when sdi check exits 10"


def test_pre_push_hook_allows_on_exit_0(
    tmp_path: Path, bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    """Pre-push hook must allow push (exit 0) when sdi check exits 0."""
    run_sdi(cli_runner, ["init", "--install-pre-push-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "pre-push"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_sdi(bin_dir, exit_code=0)

    env = {**os.environ, "PATH": str(bin_dir) + ":" + os.environ.get("PATH", "")}
    result = subprocess.run(
        [str(hook)],
        env=env,
        capture_output=True,
        cwd=str(bare_git_repo),
    )
    assert result.returncode == 0, "pre-push hook must allow push when sdi check exits 0"


# ---------------------------------------------------------------------------
# Shell syntax validation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not available")
def test_post_merge_hook_valid_shell_syntax(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    run_sdi(cli_runner, ["init", "--install-post-merge-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "post-merge"
    result = subprocess.run(["shellcheck", str(hook)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not available")
def test_pre_push_hook_valid_shell_syntax(
    bare_git_repo: Path, cli_runner: CliRunner
) -> None:
    run_sdi(cli_runner, ["init", "--install-pre-push-hook"], bare_git_repo)
    hook = bare_git_repo / ".git" / "hooks" / "pre-push"
    result = subprocess.run(["shellcheck", str(hook)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
