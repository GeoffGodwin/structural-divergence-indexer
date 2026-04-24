"""Shared test fixtures for SDI test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from sdi.cli import cli
from sdi.detection.leiden import CommunityResult
from sdi.parsing import FeatureRecord
from sdi.patterns.catalog import CategoryStats, PatternCatalog, ShapeStats
from sdi.patterns.fingerprint import PatternFingerprint
from sdi.snapshot.model import (
    SNAPSHOT_VERSION,
    DivergenceSummary,
    Snapshot,
)


# ---------------------------------------------------------------------------
# Adapter availability guards (used by integration tests)
# ---------------------------------------------------------------------------


def _has_python_adapter() -> bool:
    """Return True if the Python tree-sitter grammar is importable."""
    try:
        from sdi.parsing.python import PythonAdapter  # noqa: F401

        return True
    except Exception:  # grammar init can raise OSError, RuntimeError, etc.
        return False


def _has_ts_adapter() -> bool:
    """Return True if the TypeScript tree-sitter adapter is importable."""
    try:
        from sdi.parsing.typescript import TypeScriptAdapter  # noqa: F401

        return True
    except Exception:  # grammar init can raise OSError, RuntimeError, etc.
        return False


def _has_shell_adapter() -> bool:
    """Return True if the shell tree-sitter adapter is importable."""
    try:
        from sdi.parsing.shell import ShellAdapter  # noqa: F401

        return True
    except Exception:  # grammar init can raise OSError, RuntimeError, etc.
        return False


requires_python_adapter = pytest.mark.skipif(
    not _has_python_adapter(),
    reason="tree-sitter Python grammar not available",
)

requires_ts_adapter = pytest.mark.skipif(
    not _has_ts_adapter(),
    reason="tree-sitter TypeScript grammar not available",
)

requires_shell_adapter = pytest.mark.skipif(
    not _has_shell_adapter(),
    reason="tree-sitter Bash grammar not available",
)


@pytest.fixture
def sample_divergence() -> DivergenceSummary:
    """A DivergenceSummary with non-null current values but null deltas (first snapshot)."""
    return DivergenceSummary(
        pattern_entropy=1.5,
        pattern_entropy_delta=None,
        convention_drift=0.3,
        convention_drift_delta=None,
        coupling_topology=0.8,
        coupling_topology_delta=None,
        boundary_violations=2,
        boundary_violations_delta=None,
    )


@pytest.fixture
def sample_snapshot(sample_divergence: DivergenceSummary) -> Snapshot:
    """A complete Snapshot with known, deterministic values."""
    return Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-10T17:25:00Z",
        commit_sha="abc123def456",
        config_hash="deadbeef01234567",
        divergence=sample_divergence,
        file_count=10,
        language_breakdown={"python": 8, "markdown": 2},
    )


@pytest.fixture
def sample_feature_record() -> FeatureRecord:
    """A FeatureRecord with realistic but minimal content."""
    return FeatureRecord(
        file_path="src/foo.py",
        language="python",
        imports=["os", "pathlib"],
        symbols=["MyClass", "my_function"],
        pattern_instances=[
            {
                "category": "error_handling",
                "ast_hash": "a1b2c3d4",
                "location": {"line": 10, "col": 0},
            }
        ],
        lines_of_code=50,
    )


@pytest.fixture
def sample_config_dict() -> dict:
    """A valid minimal config dict with a few non-default values."""
    return {
        "core": {"random_seed": 99},
        "snapshots": {"retention": 50},
        "thresholds": {"pattern_entropy_rate": 3.0},
    }


@pytest.fixture
def git_repo_dir(tmp_path: Path) -> Path:
    """A temporary directory that looks like a git repository root."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def sdi_project_dir(git_repo_dir: Path) -> Path:
    """A git repo directory with an initialized .sdi/ structure."""
    sdi_dir = git_repo_dir / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    return git_repo_dir


@pytest.fixture
def sample_pattern_fingerprint() -> PatternFingerprint:
    """A PatternFingerprint with a known structural hash."""
    return PatternFingerprint(
        category="error_handling",
        structural_hash="abc12345def67890",
        node_count=10,
    )


@pytest.fixture
def sample_pattern_catalog() -> PatternCatalog:
    """A PatternCatalog with two error_handling shapes for round-trip and velocity tests."""
    shapes = {
        "hash_a": ShapeStats(
            structural_hash="hash_a",
            instance_count=3,
            file_paths=["src/a.py", "src/b.py"],
            velocity=None,
            boundary_spread=None,
        ),
        "hash_b": ShapeStats(
            structural_hash="hash_b",
            instance_count=1,
            file_paths=["src/c.py"],
            velocity=None,
            boundary_spread=None,
        ),
    }
    cat = CategoryStats(name="error_handling", shapes=shapes)
    return PatternCatalog(categories={"error_handling": cat})


@pytest.fixture
def sample_community_result() -> CommunityResult:
    """A CommunityResult with two clusters over four files."""
    return CommunityResult(
        partition=[0, 0, 1, 1],
        stability_score=1.0,
        cluster_count=2,
        inter_cluster_edges=[],
        surface_area_ratios={0: 0.0, 1: 0.0},
        vertex_names=["src/a.py", "src/b.py", "src/c.py", "src/d.py"],
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    """A Click CliRunner for invoking SDI commands in tests."""
    return CliRunner()


def run_sdi(
    runner: CliRunner,
    args: list[str],
    cwd: Path,
    **kwargs: Any,
) -> Any:
    """Invoke the SDI CLI with a specified working directory.

    Args:
        runner: Click CliRunner instance.
        args: CLI argument list (e.g., ["show", "--format", "json"]).
        cwd: Directory to use as the working directory for the invocation.
        **kwargs: Extra kwargs forwarded to runner.invoke().

    Returns:
        Click Result object.
    """
    import os

    orig_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return runner.invoke(cli, args, catch_exceptions=False, **kwargs)
    finally:
        os.chdir(orig_cwd)


@pytest.fixture
def sdi_project_with_snapshot(
    sdi_project_dir: Path,
    sample_snapshot: Snapshot,
) -> Path:
    """An initialized SDI project directory with one snapshot on disk."""
    from sdi.snapshot.storage import write_snapshot

    snapshots_dir = sdi_project_dir / ".sdi" / "snapshots"
    write_snapshot(sample_snapshot, snapshots_dir)
    return sdi_project_dir
