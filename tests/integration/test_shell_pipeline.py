"""Shell language pipeline integration tests.

Tests the end-to-end snapshot workflow against the simple-shell fixture.
Gated by requires_shell_adapter; skipped when tree-sitter-bash is absent.
"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import pytest

from tests.conftest import requires_shell_adapter, run_sdi

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def shell_project(tmp_path: Path) -> Path:
    """Initialized SDI project populated with the simple-shell fixture files."""
    fixture = FIXTURES_DIR / "simple-shell"
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()

    for src in fixture.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(fixture)
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if src.stat().st_mode & stat.S_IXUSR:
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return tmp_path


def _make_shell_project(tmp_path: Path, fixture_name: str) -> Path:
    """Copy a shell fixture into tmp_path preserving directory structure."""
    fixture = FIXTURES_DIR / fixture_name
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    for src in fixture.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(fixture)
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if src.stat().st_mode & stat.S_IXUSR:
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return tmp_path


@pytest.fixture
def shell_heavy_project(tmp_path: Path) -> Path:
    """Initialized SDI project with the shell-heavy fixture (>= 2 source edges)."""
    return _make_shell_project(tmp_path, "shell-heavy")


@pytest.fixture
def shell_graph_project(tmp_path: Path) -> Path:
    """Initialized SDI project with the shell-graph fixture (8 scripts, 12+ edges)."""
    return _make_shell_project(tmp_path, "shell-graph")


@requires_shell_adapter
class TestShellPipeline:
    """End-to-end pipeline tests against the simple-shell fixture."""

    def test_snapshot_detects_three_shell_files(self, cli_runner, shell_project):
        """Snapshot reports language_breakdown['shell'] == 3."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["language_breakdown"].get("shell") == 3

    def test_catalog_contains_error_handling_and_logging(self, cli_runner, shell_project):
        """Catalog from simple-shell includes error_handling and logging categories."""
        run_sdi(cli_runner, ["-q", "snapshot"], shell_project)
        result = run_sdi(cli_runner, ["--format", "json", "catalog"], shell_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        categories = data["catalog"]["categories"]
        assert "error_handling" in categories
        assert "logging" in categories

    def test_edge_count_at_least_one(self, cli_runner, shell_project):
        """M15 acceptance: simple-shell source edge resolves."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["edge_count"] >= 1


@requires_shell_adapter
class TestShellHeavyGraph:
    """M15 acceptance: shell-heavy fixture produces >= 2 edges and connected graph."""

    def test_edge_count_at_least_two(self, cli_runner, shell_heavy_project):
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_heavy_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["edge_count"] >= 2

    def test_component_count_less_than_file_count(self, cli_runner, shell_heavy_project):
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_heavy_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["component_count"] <= data["file_count"] - 1


@requires_shell_adapter
class TestShellGraphFixture:
    """M15 acceptance: shell-graph fixture produces >= 12 edges and <= 4 components."""

    def test_edge_count_at_least_12(self, cli_runner, shell_graph_project):
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_graph_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["edge_count"] >= 12

    def test_component_count_at_most_4(self, cli_runner, shell_graph_project):
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], shell_graph_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["component_count"] <= 4


@requires_shell_adapter
class TestShellNoEdges:
    """Shell-only repo with no source directives produces a valid snapshot with edge_count=0.

    This is the base case for M15: a repository whose shell scripts have no
    source/. directives must not crash. edge_count==0 and each file forms its
    own weakly-connected component (component_count == file_count).
    """

    @pytest.fixture
    def no_source_project(self, tmp_path: Path) -> Path:
        """Three shell scripts with no source directives, no shared dependencies."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".sdi" / "snapshots").mkdir(parents=True)
        scripts = {
            "alpha.sh": "#!/usr/bin/env bash\necho 'alpha'\n",
            "beta.sh": "#!/usr/bin/env bash\necho 'beta'\n",
            "gamma.sh": "#!/usr/bin/env bash\necho 'gamma'\n",
        }
        for name, content in scripts.items():
            (tmp_path / name).write_text(content, encoding="utf-8")
        return tmp_path

    def test_snapshot_exits_zero(self, cli_runner, no_source_project):
        """sdi snapshot must succeed (exit 0) for a shell repo with no source edges."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], no_source_project)
        assert result.exit_code == 0, result.output

    def test_edge_count_is_zero(self, cli_runner, no_source_project):
        """Graph has zero edges when no shell script sources another."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], no_source_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["edge_count"] == 0

    def test_component_count_equals_file_count(self, cli_runner, no_source_project):
        """Each isolated shell file is its own weakly-connected component."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], no_source_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["graph_metrics"]["component_count"] == data["file_count"]

    def test_language_breakdown_is_shell_only(self, cli_runner, no_source_project):
        """language_breakdown contains only 'shell' for a repo with only .sh files."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], no_source_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        breakdown = data["language_breakdown"]
        assert set(breakdown.keys()) == {"shell"}
        assert breakdown["shell"] == 3
