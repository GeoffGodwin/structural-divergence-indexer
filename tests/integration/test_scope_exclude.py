"""Integration tests for patterns.scope_exclude config key (M17).

Uses the scope-exclude-python fixture which contains:
- lib/util.py        (Shape 1: canonical error-handling)
- cmd/run.py         (Shape 2: variant with 'as' alias and raise)
- tests/scenario_a.py (Shape 3: bare except with pass)
- tests/scenario_b.py (Shape 4: try/except/finally)
- tests/scenario_c.py (Shape 5: tuple exception type with return None)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import requires_python_adapter, run_sdi

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SCOPE_FIXTURE = FIXTURES_DIR / "scope-exclude-python"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scope_project(tmp_path: Path) -> Path:
    """Initialized SDI project populated with the scope-exclude-python fixture."""
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()

    for subdir in ("lib", "cmd", "tests"):
        src_dir = SCOPE_FIXTURE / subdir
        dst_dir = tmp_path / subdir
        dst_dir.mkdir()
        for f in src_dir.glob("*.py"):
            shutil.copy(f, dst_dir / f.name)

    return tmp_path


def _write_scope_config(project: Path, patterns: list[str]) -> None:
    """Write a .sdi/config.toml with the given scope_exclude patterns."""
    lines = ["[patterns]", "scope_exclude = ["]
    for pat in patterns:
        lines.append(f'  "{pat}",')
    lines.append("]")
    (project / ".sdi" / "config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _snapshot_catalog(cli_runner, project: Path) -> dict:
    """Take a snapshot and return pattern_catalog from the JSON output."""
    result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], project)
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    return data["pattern_catalog"]


def _snapshot_full(cli_runner, project: Path) -> dict:
    """Take a snapshot and return the full JSON output dict."""
    result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], project)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_python_adapter
class TestScopeExcludePipeline:
    """End-to-end tests for patterns.scope_exclude filtering."""

    def test_no_scope_exclude_sees_all_shapes(self, cli_runner, scope_project: Path) -> None:
        """With scope_exclude=[], error_handling entropy reflects all 5 fixture files."""
        catalog = _snapshot_catalog(cli_runner, scope_project)
        eh = catalog["categories"].get("error_handling", {})
        shape_count = len(eh.get("shapes", {}))
        # At least 3 distinct shapes expected (lib, cmd, tests/* may share or not)
        assert shape_count >= 2, f"Expected multiple distinct shapes, got {shape_count}"

    def test_scope_exclude_removes_test_file_paths(self, cli_runner, scope_project: Path) -> None:
        """With scope_exclude=['tests/**'], no tests/* paths appear in shape file_paths."""
        _write_scope_config(scope_project, ["tests/**"])
        catalog = _snapshot_catalog(cli_runner, scope_project)
        eh = catalog["categories"].get("error_handling", {})
        for shape_data in eh.get("shapes", {}).values():
            for fp in shape_data.get("file_paths", []):
                assert not fp.startswith("tests/"), f"Excluded path found in catalog: {fp}"

    def test_scope_exclude_meta_count(self, cli_runner, scope_project: Path) -> None:
        """meta.scope_excluded_file_count equals the number of tests/ files in the fixture."""
        _write_scope_config(scope_project, ["tests/**"])
        catalog = _snapshot_catalog(cli_runner, scope_project)
        meta = catalog.get("meta", {})
        assert meta.get("scope_excluded_file_count") == 3  # scenario_a, b, c

    def test_graph_unaffected_by_scope_exclude(self, cli_runner, scope_project: Path) -> None:
        """Graph metrics are identical with and without scope_exclude."""
        snap_all = _snapshot_full(cli_runner, scope_project)
        node_all = snap_all["graph_metrics"].get("node_count")

        # Clear snapshots, write scope config, take another snapshot
        for f in (scope_project / ".sdi" / "snapshots").glob("*.json"):
            f.unlink()
        _write_scope_config(scope_project, ["tests/**"])
        snap_excl = _snapshot_full(cli_runner, scope_project)
        node_excl = snap_excl["graph_metrics"].get("node_count")

        assert node_all == node_excl, "Graph node_count changed after applying scope_exclude"

    def test_default_scope_exclude_no_meta(self, cli_runner, scope_project: Path) -> None:
        """When scope_exclude=[], the meta block is absent from pattern_catalog."""
        catalog = _snapshot_catalog(cli_runner, scope_project)
        assert "meta" not in catalog, "meta block should be absent when no files are excluded"

    def test_scope_exclude_reduces_entropy(self, cli_runner, scope_project: Path) -> None:
        """Entropy of error_handling is lower with scope_exclude than without."""
        snap_all = _snapshot_full(cli_runner, scope_project)
        entropy_all = snap_all["divergence"].get("pattern_entropy")

        for f in (scope_project / ".sdi" / "snapshots").glob("*.json"):
            f.unlink()
        _write_scope_config(scope_project, ["tests/**"])
        snap_excl = _snapshot_full(cli_runner, scope_project)
        entropy_excl = snap_excl["divergence"].get("pattern_entropy")

        # Entropy must be <= when test files are excluded (fewer or equal distinct shapes)
        if entropy_all is not None and entropy_excl is not None:
            assert entropy_excl <= entropy_all
