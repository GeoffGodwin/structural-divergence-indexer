"""Unit tests for sdi.cli._helpers — resolve_snapshots_dir path validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.cli._helpers import resolve_snapshots_dir
from sdi.config import SDIConfig, SnapshotsConfig


def _config_with_dir(snapshots_dir: str) -> SDIConfig:
    """Build a minimal SDIConfig with the given snapshots.dir value."""
    config = SDIConfig()
    config.snapshots = SnapshotsConfig(dir=snapshots_dir)
    return config


class TestResolveSnapshotsDirHappyPath:
    """resolve_snapshots_dir returns the expected path for valid inputs."""

    def test_default_dir_returns_path_inside_repo(self, tmp_path: Path) -> None:
        config = _config_with_dir(".sdi/snapshots")
        result = resolve_snapshots_dir(tmp_path, config)
        assert result == tmp_path / ".sdi" / "snapshots"

    def test_nested_custom_dir_returns_correct_path(self, tmp_path: Path) -> None:
        config = _config_with_dir("my/custom/snapshots")
        result = resolve_snapshots_dir(tmp_path, config)
        assert result == tmp_path / "my" / "custom" / "snapshots"

    def test_single_level_dir_returns_correct_path(self, tmp_path: Path) -> None:
        config = _config_with_dir("snaps")
        result = resolve_snapshots_dir(tmp_path, config)
        assert result == tmp_path / "snaps"

    def test_result_is_relative_to_repo_root(self, tmp_path: Path) -> None:
        config = _config_with_dir(".sdi/snapshots")
        result = resolve_snapshots_dir(tmp_path, config)
        # The result must be under the repo root
        assert result.resolve().is_relative_to(tmp_path.resolve())


class TestResolveSnapshotsDirPathTraversalRejection:
    """resolve_snapshots_dir raises SystemExit(2) for paths escaping the repo root."""

    def test_two_level_dotdot_raises_sysexit_2(self, tmp_path: Path) -> None:
        config = _config_with_dir("../../etc")
        with pytest.raises(SystemExit) as exc_info:
            resolve_snapshots_dir(tmp_path, config)
        assert exc_info.value.code == 2

    def test_one_level_dotdot_from_root_raises_sysexit_2(self, tmp_path: Path) -> None:
        # Create a sub-directory to act as the repo root so that "../" escapes it
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        config = _config_with_dir("../outside")
        with pytest.raises(SystemExit) as exc_info:
            resolve_snapshots_dir(repo_root, config)
        assert exc_info.value.code == 2

    def test_absolute_path_outside_repo_raises_sysexit_2(self, tmp_path: Path) -> None:
        # Use an absolute path to /tmp which will not be relative to the repo root
        # (unless tmp_path happens to be /tmp itself; we use a known sub-path)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        outside = str(tmp_path)  # parent of repo_root — clearly outside
        config = _config_with_dir(outside)
        with pytest.raises(SystemExit) as exc_info:
            resolve_snapshots_dir(repo_root, config)
        assert exc_info.value.code == 2

    def test_traversal_via_symlink_component_raises_sysexit_2(
        self, tmp_path: Path
    ) -> None:
        # ../../secrets is a traversal pattern regardless of depth
        config = _config_with_dir("../../secrets/credentials")
        with pytest.raises(SystemExit) as exc_info:
            resolve_snapshots_dir(tmp_path, config)
        assert exc_info.value.code == 2

    def test_sysexit_code_is_2_not_1_or_3(self, tmp_path: Path) -> None:
        """Exit code must be exactly 2 (config/env error) per CLAUDE.md exit code contract."""
        config = _config_with_dir("../../etc/passwd")
        with pytest.raises(SystemExit) as exc_info:
            resolve_snapshots_dir(tmp_path, config)
        assert exc_info.value.code == 2
        assert exc_info.value.code != 1
        assert exc_info.value.code != 3
