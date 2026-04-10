"""Shared test fixtures for SDI test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.snapshot.model import (
    SNAPSHOT_VERSION,
    DivergenceSummary,
    FeatureRecord,
    Snapshot,
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
        pattern_instances=[{"type": "function_def", "name": "my_function", "size": 12}],
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
