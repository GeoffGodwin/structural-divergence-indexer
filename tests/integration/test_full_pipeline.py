"""Full end-to-end pipeline integration tests.

Tests the complete init → snapshot → show → catalog workflow against
real source fixtures (simple-python, multi-language, high-entropy).
Skipped when tree-sitter grammars are unavailable.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import (
    requires_python_adapter,
    requires_ts_adapter,
    run_sdi,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _has_igraph() -> bool:
    """Check whether igraph is available."""
    try:
        import igraph  # noqa: F401

        return True
    except ImportError:
        return False


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


# ---------------------------------------------------------------------------
# Multi-language fixture tests
# ---------------------------------------------------------------------------


@pytest.fixture
def multilang_project(tmp_path: Path) -> Path:
    """Initialized SDI project populated with multi-language fixture files."""
    fixture = FIXTURES_DIR / "multi-language"
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    for f in fixture.iterdir():
        if f.suffix in (".py", ".ts"):
            shutil.copy(f, tmp_path / f.name)
    return tmp_path


@requires_python_adapter
class TestMultiLanguagePipeline:
    """Pipeline tests against the multi-language (Python + TypeScript) fixture."""

    def test_snapshot_detects_python_files(self, cli_runner, multilang_project):
        """Snapshot detects Python files in a multi-language project."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], multilang_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "python" in data["language_breakdown"]

    @requires_ts_adapter
    def test_snapshot_detects_both_languages(self, cli_runner, multilang_project):
        """Snapshot detects both Python and TypeScript files."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], multilang_project
        )
        assert result.exit_code == 0, result.output
        breakdown = json.loads(result.output)["language_breakdown"]
        assert "python" in breakdown and "typescript" in breakdown


# ---------------------------------------------------------------------------
# High-entropy fixture tests
# ---------------------------------------------------------------------------


@pytest.fixture
def high_entropy_project(tmp_path: Path) -> Path:
    """Initialized SDI project populated with high-entropy fixture files."""
    fixture = FIXTURES_DIR / "high-entropy"
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    for f in fixture.glob("*.py"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


@requires_python_adapter
class TestHighEntropyPipeline:
    """Pipeline tests against the deliberately high-entropy fixture."""

    def test_snapshot_exits_0(self, cli_runner, high_entropy_project):
        """sdi snapshot exits 0 on the high-entropy fixture."""
        result = run_sdi(cli_runner, ["-q", "snapshot"], high_entropy_project)
        assert result.exit_code == 0, result.output

    def test_catalog_contains_error_handling(self, cli_runner, high_entropy_project):
        """Catalog from high-entropy fixture includes error_handling category."""
        run_sdi(cli_runner, ["-q", "snapshot"], high_entropy_project)
        result = run_sdi(
            cli_runner, ["--format", "json", "catalog"], high_entropy_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "error_handling" in data["catalog"]["categories"]

    def test_snapshot_file_count(self, cli_runner, high_entropy_project):
        """Snapshot records correct file count for the high-entropy fixture."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], high_entropy_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["file_count"] >= 10


# ---------------------------------------------------------------------------
# sdi init → snapshot lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture
def bare_git_repo(tmp_path: Path) -> Path:
    """A bare git repository with NO .sdi/ directory (pre-init state)."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text(
        "def greet(name: str) -> str:\n    return f'Hello, {name}'\n",
        encoding="utf-8",
    )
    return tmp_path


@requires_python_adapter
class TestInitAndSnapshot:
    """Covers the `sdi init` command followed by `sdi snapshot`."""

    def test_init_creates_sdi_structure(self, cli_runner, bare_git_repo):
        """sdi init creates .sdi/config.toml and .sdi/snapshots/ in a git repo."""
        result = run_sdi(cli_runner, ["init"], bare_git_repo)
        assert result.exit_code == 0, result.output
        assert (bare_git_repo / ".sdi" / "config.toml").exists()
        assert (bare_git_repo / ".sdi" / "snapshots").is_dir()

    def test_init_then_snapshot_exits_0(self, cli_runner, bare_git_repo):
        """sdi init followed by sdi snapshot exits 0 and writes a snapshot file."""
        init_result = run_sdi(cli_runner, ["init"], bare_git_repo)
        assert init_result.exit_code == 0, init_result.output

        snap_result = run_sdi(cli_runner, ["-q", "snapshot"], bare_git_repo)
        assert snap_result.exit_code == 0, snap_result.output

        snapshots = list((bare_git_repo / ".sdi" / "snapshots").glob("snapshot_*.json"))
        assert len(snapshots) == 1

    def test_init_idempotent(self, cli_runner, bare_git_repo):
        """Running sdi init twice does not error and does not overwrite config."""
        run_sdi(cli_runner, ["init"], bare_git_repo)
        config_path = bare_git_repo / ".sdi" / "config.toml"
        mtime_after_first = config_path.stat().st_mtime_ns

        result = run_sdi(cli_runner, ["init"], bare_git_repo)
        assert result.exit_code == 0, result.output
        # Without --force, the second init should not overwrite config
        assert config_path.stat().st_mtime_ns == mtime_after_first
