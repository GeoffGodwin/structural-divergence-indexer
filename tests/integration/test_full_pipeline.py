"""Full end-to-end pipeline integration tests.

Tests the complete init → snapshot → show → catalog workflow against
a real source fixture. Skipped when tree-sitter grammars are unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import run_sdi


def _has_python_adapter() -> bool:
    """Check whether the Python tree-sitter adapter can be imported."""
    try:
        from sdi.parsing.python import PythonAdapter  # noqa: F401
        return True
    except (ImportError, Exception):
        return False


def _has_igraph() -> bool:
    """Check whether igraph is available."""
    try:
        import igraph  # noqa: F401
        return True
    except ImportError:
        return False


requires_python_adapter = pytest.mark.skipif(
    not _has_python_adapter(),
    reason="tree-sitter Python grammar not available",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def initialized_project(tmp_path: Path) -> Path:
    """An initialized SDI project pointing at the simple-python fixture."""
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()

    # Write a minimal Python source file for parsing
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text(
        "import os\n\ndef greet(name: str) -> str:\n    return f'Hello, {name}'\n",
        encoding="utf-8",
    )
    (src_dir / "utils.py").write_text(
        "from src import main\n\ndef helper() -> None:\n    pass\n",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_python_adapter
class TestFullSnapshotWorkflow:
    """End-to-end snapshot → show → catalog workflow."""

    def test_snapshot_exits_0(self, cli_runner, initialized_project):
        """sdi snapshot exits 0 and writes a snapshot file."""
        result = run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        assert result.exit_code == 0, result.output

        snapshots_dir = initialized_project / ".sdi" / "snapshots"
        snapshot_files = list(snapshots_dir.glob("snapshot_*.json"))
        assert len(snapshot_files) == 1

    def test_snapshot_json_output(self, cli_runner, initialized_project):
        """sdi snapshot --format json -q outputs valid snapshot JSON."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], initialized_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "snapshot_version" in data
        assert data["file_count"] >= 1

    def test_show_after_snapshot(self, cli_runner, initialized_project):
        """sdi show works after sdi snapshot."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(cli_runner, ["show"], initialized_project)
        assert result.exit_code == 0
        assert "pattern_entropy" in result.output

    def test_catalog_after_snapshot(self, cli_runner, initialized_project):
        """sdi catalog works after sdi snapshot and returns JSON catalog."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(
            cli_runner, ["-q", "--format", "json", "catalog"], initialized_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "catalog" in data
        assert "categories" in data["catalog"]

    def test_check_first_snapshot_exits_0(self, cli_runner, initialized_project):
        """sdi check on first snapshot exits 0 (null deltas, no breach)."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(cli_runner, ["check"], initialized_project)
        assert result.exit_code == 0

    def test_two_snapshots_diff(self, cli_runner, initialized_project):
        """sdi diff works after two snapshots."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(cli_runner, ["diff"], initialized_project)
        assert result.exit_code == 0
        assert "→" in result.output

    def test_trend_two_snapshots_json(self, cli_runner, initialized_project):
        """sdi trend after two snapshots returns two timestamps."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(
            cli_runner, ["-q", "--format", "json", "trend"], initialized_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["timestamps"]) == 2

    def test_snapshot_writes_feature_records(self, cli_runner, initialized_project):
        """Snapshot JSON includes file_count > 0 for a project with Python files."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], initialized_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["file_count"] > 0

    def test_trend_dimension_filter(self, cli_runner, initialized_project):
        """sdi trend --dimension filters output to only the requested dimension."""
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)
        result = run_sdi(
            cli_runner,
            ["-q", "--format", "json", "trend", "--dimension", "pattern_entropy"],
            initialized_project,
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        # Only the requested dimension should be present
        assert "pattern_entropy" in data["dimensions"]
        # No other dimensions should appear in the output
        assert set(data["dimensions"].keys()) == {"pattern_entropy"}

    def test_retention_enforced(self, cli_runner, initialized_project):
        """Retention limit is enforced: with retention=2, old snapshots are pruned."""
        config_content = "[snapshots]\nretention = 2\n"
        (initialized_project / ".sdi" / "config.toml").write_text(
            config_content, encoding="utf-8"
        )
        for _ in range(4):
            run_sdi(cli_runner, ["-q", "snapshot"], initialized_project)

        snapshots_dir = initialized_project / ".sdi" / "snapshots"
        snapshot_files = list(snapshots_dir.glob("snapshot_*.json"))
        assert len(snapshot_files) <= 2
