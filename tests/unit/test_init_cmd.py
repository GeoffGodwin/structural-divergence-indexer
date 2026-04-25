"""Unit tests for sdi.cli.init_cmd private helpers.

Covers:
- _maybe_install_hooks: TTY-prompt branch (click.confirm path)
- _maybe_install_hooks: non-TTY path (no prompt, respects flags)
- _infer_boundaries_from_snapshot: success path (partition data present)
- _infer_boundaries_from_snapshot: fallback paths (no snapshots, empty data)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdi.cli._hooks import POST_MERGE_MARKER, PRE_PUSH_MARKER
from sdi.cli.init_cmd import _infer_boundaries_from_snapshot, _maybe_install_hooks
from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, Snapshot
from sdi.snapshot.storage import write_snapshot

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_root_with_hooks(tmp_path: Path) -> Path:
    """A temporary directory that looks like a git repo root with a hooks dir."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sdi_dir_with_snapshot(tmp_path: Path) -> Path:
    """An .sdi/ directory containing one snapshot with valid partition_data."""
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    snapshots_dir = sdi_dir / "snapshots"
    snapshots_dir.mkdir()

    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-24T12:00:00Z",
        commit_sha="abc123def456",
        config_hash="deadbeef01234567",
        divergence=DivergenceSummary(),
        file_count=3,
        language_breakdown={"python": 3},
        partition_data={
            "vertex_names": ["src/a.py", "src/b.py", "src/c.py"],
            "partition": [0, 0, 1],
            "cluster_count": 2,
        },
    )
    write_snapshot(snap, snapshots_dir)
    return sdi_dir


# ---------------------------------------------------------------------------
# _maybe_install_hooks: TTY-prompt branch
# ---------------------------------------------------------------------------


def test_maybe_install_hooks_tty_yes_yes_installs_both(
    git_root_with_hooks: Path,
) -> None:
    """TTY path: confirming both prompts installs both hooks."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm", side_effect=[True, True]):
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=False,
            install_pre_push=False,
        )

    hooks_dir = git_root_with_hooks / ".git" / "hooks"
    post_merge = hooks_dir / "post-merge"
    pre_push = hooks_dir / "pre-push"

    assert post_merge.exists(), "post-merge hook should be installed when user confirms"
    assert POST_MERGE_MARKER in post_merge.read_text(encoding="utf-8")
    assert pre_push.exists(), "pre-push hook should be installed when user confirms"
    assert PRE_PUSH_MARKER in pre_push.read_text(encoding="utf-8")


def test_maybe_install_hooks_tty_yes_no_installs_only_post_merge(
    git_root_with_hooks: Path,
) -> None:
    """TTY path: confirming post-merge but declining pre-push installs only post-merge."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm", side_effect=[True, False]):
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=False,
            install_pre_push=False,
        )

    hooks_dir = git_root_with_hooks / ".git" / "hooks"
    assert (hooks_dir / "post-merge").exists()
    assert not (hooks_dir / "pre-push").exists()


def test_maybe_install_hooks_tty_no_no_installs_nothing(
    git_root_with_hooks: Path,
) -> None:
    """TTY path: declining both prompts leaves no hook files created."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm", side_effect=[False, False]):
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=False,
            install_pre_push=False,
        )

    hooks_dir = git_root_with_hooks / ".git" / "hooks"
    assert not (hooks_dir / "post-merge").exists()
    assert not (hooks_dir / "pre-push").exists()


def test_maybe_install_hooks_tty_prompts_twice(git_root_with_hooks: Path) -> None:
    """TTY path: click.confirm must be called exactly twice (once per hook)."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = True

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm", side_effect=[False, False]) as mock_confirm:
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=False,
            install_pre_push=False,
        )

    assert mock_confirm.call_count == 2, f"Expected 2 confirm prompts, got {mock_confirm.call_count}"


# ---------------------------------------------------------------------------
# _maybe_install_hooks: non-TTY path
# ---------------------------------------------------------------------------


def test_maybe_install_hooks_non_tty_no_flags_no_prompts(
    git_root_with_hooks: Path,
) -> None:
    """Non-TTY stdin with no flags: confirm must never be called; no hooks installed."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm") as mock_confirm:
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=False,
            install_pre_push=False,
        )

    mock_confirm.assert_not_called()
    hooks_dir = git_root_with_hooks / ".git" / "hooks"
    assert not (hooks_dir / "post-merge").exists()
    assert not (hooks_dir / "pre-push").exists()


def test_maybe_install_hooks_flag_bypasses_tty_check(
    git_root_with_hooks: Path,
) -> None:
    """Explicit --install-post-merge-hook flag installs without any TTY check."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False

    with patch.object(sys, "stdin", mock_stdin), patch("click.confirm") as mock_confirm:
        _maybe_install_hooks(
            git_root_with_hooks,
            install_post_merge=True,
            install_pre_push=False,
        )

    mock_confirm.assert_not_called()
    assert (git_root_with_hooks / ".git" / "hooks" / "post-merge").exists()


def test_maybe_install_hooks_missing_hooks_dir_is_noop(tmp_path: Path) -> None:
    """When .git/hooks/ does not exist, _maybe_install_hooks returns immediately."""
    # No .git/hooks dir — just a bare tmp_path
    (tmp_path / ".git").mkdir()

    _maybe_install_hooks(tmp_path, install_post_merge=True, install_pre_push=True)

    # Nothing should be created since hooks_dir doesn't exist
    assert not (tmp_path / ".git" / "hooks").exists()


# ---------------------------------------------------------------------------
# _infer_boundaries_from_snapshot: success path
# ---------------------------------------------------------------------------


def test_infer_boundaries_from_snapshot_returns_yaml_string(
    sdi_dir_with_snapshot: Path,
) -> None:
    """Happy path: returns a non-empty YAML string when partition_data is present."""
    result = _infer_boundaries_from_snapshot(sdi_dir_with_snapshot)

    assert result is not None, "_infer_boundaries_from_snapshot returned None unexpectedly"
    assert isinstance(result, str)
    assert len(result) > 0


def test_infer_boundaries_from_snapshot_yaml_has_sdi_boundaries_key(
    sdi_dir_with_snapshot: Path,
) -> None:
    """Returned YAML must start with the sdi_boundaries root key."""
    result = _infer_boundaries_from_snapshot(sdi_dir_with_snapshot)
    assert result is not None
    assert "sdi_boundaries:" in result


def test_infer_boundaries_from_snapshot_yaml_contains_cluster_names(
    sdi_dir_with_snapshot: Path,
) -> None:
    """Generated YAML must contain cluster names derived from Leiden partition IDs."""
    result = _infer_boundaries_from_snapshot(sdi_dir_with_snapshot)
    assert result is not None
    # Partition has clusters 0 and 1
    assert "cluster_0" in result
    assert "cluster_1" in result


def test_infer_boundaries_from_snapshot_yaml_contains_file_paths(
    sdi_dir_with_snapshot: Path,
) -> None:
    """Generated YAML must list the vertex file paths from partition_data."""
    result = _infer_boundaries_from_snapshot(sdi_dir_with_snapshot)
    assert result is not None
    # At least some file paths from the snapshot should appear
    assert "src/a.py" in result or "src/b.py" in result or "src/c.py" in result


# ---------------------------------------------------------------------------
# _infer_boundaries_from_snapshot: fallback paths
# ---------------------------------------------------------------------------


def test_infer_boundaries_no_snapshots_dir_returns_none(tmp_path: Path) -> None:
    """When snapshots/ directory does not exist, returns None."""
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    # No snapshots sub-directory created

    result = _infer_boundaries_from_snapshot(sdi_dir)
    assert result is None


def test_infer_boundaries_empty_snapshots_dir_returns_none(tmp_path: Path) -> None:
    """When snapshots/ exists but is empty, returns None."""
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()

    result = _infer_boundaries_from_snapshot(sdi_dir)
    assert result is None


def test_infer_boundaries_snapshot_no_partition_data_returns_none(
    tmp_path: Path,
) -> None:
    """When the latest snapshot has no partition_data, returns None."""
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    snapshots_dir = sdi_dir / "snapshots"
    snapshots_dir.mkdir()

    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-24T12:00:00Z",
        commit_sha="abc123",
        config_hash="deadbeef",
        divergence=DivergenceSummary(),
        file_count=0,
        language_breakdown={},
        partition_data={},  # empty — no partition data
    )
    write_snapshot(snap, snapshots_dir)

    result = _infer_boundaries_from_snapshot(sdi_dir)
    assert result is None


def test_infer_boundaries_snapshot_no_vertex_names_returns_none(
    tmp_path: Path,
) -> None:
    """When partition_data lacks vertex_names, returns None."""
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    snapshots_dir = sdi_dir / "snapshots"
    snapshots_dir.mkdir()

    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-24T12:00:00Z",
        commit_sha="abc123",
        config_hash="deadbeef",
        divergence=DivergenceSummary(),
        file_count=2,
        language_breakdown={"python": 2},
        partition_data={
            "cluster_count": 1,
            # vertex_names key is absent
        },
    )
    write_snapshot(snap, snapshots_dir)

    result = _infer_boundaries_from_snapshot(sdi_dir)
    assert result is None
