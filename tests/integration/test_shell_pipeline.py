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
            dest.chmod(
                dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

    return tmp_path


@requires_shell_adapter
class TestShellPipeline:
    """End-to-end pipeline tests against the simple-shell fixture."""

    def test_snapshot_detects_three_shell_files(self, cli_runner, shell_project):
        """Snapshot reports language_breakdown['shell'] == 3."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], shell_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["language_breakdown"].get("shell") == 3

    def test_catalog_contains_error_handling_and_logging(
        self, cli_runner, shell_project
    ):
        """Catalog from simple-shell includes error_handling and logging categories."""
        run_sdi(cli_runner, ["-q", "snapshot"], shell_project)
        result = run_sdi(
            cli_runner, ["--format", "json", "catalog"], shell_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        categories = data["catalog"]["categories"]
        assert "error_handling" in categories
        assert "logging" in categories
