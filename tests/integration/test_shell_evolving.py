"""Integration tests for evolving-shell fixture: init → snapshot×4 → diff → trend → check.

All tests are gated by requires_shell_adapter.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests.conftest import requires_shell_adapter, run_sdi
from click.testing import CliRunner
from sdi.patterns.catalog import PatternCatalog
from sdi.snapshot.storage import list_snapshots, read_snapshot


def _load_setup_fixture():
    spec = importlib.util.spec_from_file_location(
        "setup_fixture_shell",
        Path(__file__).parent.parent / "fixtures" / "evolving-shell" / "setup_fixture.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
@requires_shell_adapter
def evolving_shell_repo(tmp_path_factory):
    """Create a fresh evolving-shell git repo and capture 4 snapshots."""
    mod = _load_setup_fixture()
    repo_dir = tmp_path_factory.mktemp("evolving_shell") / "repo"
    mod.create_evolving_fixture(repo_dir)

    runner = CliRunner()

    def _sdi(*args):
        return run_sdi(runner, list(args), cwd=repo_dir)

    commits = subprocess.run(
        ["git", "log", "--oneline", "--reverse"],
        cwd=repo_dir, capture_output=True, text=True,
    ).stdout.strip().split("\n")

    snapshots_dir = repo_dir / ".sdi" / "snapshots"
    result = _sdi("init")
    assert result.exit_code == 0, result.output

    for commit_line in commits:
        sha = commit_line.split()[0]
        subprocess.run(["git", "checkout", sha], cwd=repo_dir, capture_output=True, check=True)
        result = _sdi("snapshot")
        assert result.exit_code == 0, f"snapshot failed at {sha}: {result.output}"

    subprocess.run(["git", "checkout", "main"], cwd=repo_dir, capture_output=True)

    snapshot_paths = list_snapshots(snapshots_dir)
    assert len(snapshot_paths) == 4, f"Expected 4 snapshots, got {len(snapshot_paths)}"

    snaps = [read_snapshot(p) for p in snapshot_paths]
    return repo_dir, snaps


# ---------------------------------------------------------------------------
# C1 baseline assertions
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestC1Baseline:
    def test_c1_all_deltas_none(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c1 = snaps[0]
        assert c1.divergence.pattern_entropy_delta is None
        assert c1.divergence.convention_drift_delta is None
        assert c1.divergence.coupling_topology_delta is None
        assert c1.divergence.boundary_violations_delta is None


# ---------------------------------------------------------------------------
# C1→C2: drift assertions
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestC1ToC2Drift:
    def test_error_handling_entropy_increases(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c1_eh = _cat_entropy(snaps[0], "error_handling")
        c2_eh = _cat_entropy(snaps[1], "error_handling")
        assert c2_eh - c1_eh >= 2

    def test_logging_entropy_increases(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c1_log = _cat_entropy(snaps[0], "logging")
        c2_log = _cat_entropy(snaps[1], "logging")
        assert c2_log - c1_log >= 1

    def test_convention_drift_positive(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        assert snaps[1].divergence.convention_drift_delta is not None
        assert snaps[1].divergence.convention_drift_delta > 0


# ---------------------------------------------------------------------------
# C2→C3: consolidation assertions
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestC2ToC3Consolidation:
    def test_error_handling_entropy_decreases(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c2_eh = _cat_entropy(snaps[1], "error_handling")
        c3_eh = _cat_entropy(snaps[2], "error_handling")
        assert c3_eh - c2_eh <= -1

    def test_convention_drift_negative(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        assert snaps[2].divergence.convention_drift_delta is not None
        assert snaps[2].divergence.convention_drift_delta < 0


# ---------------------------------------------------------------------------
# C3→C4: regression assertions
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestC3ToC4Regression:
    def test_error_handling_entropy_increases(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c3_eh = _cat_entropy(snaps[2], "error_handling")
        c4_eh = _cat_entropy(snaps[3], "error_handling")
        assert c4_eh - c3_eh >= 1

    def test_async_patterns_appears(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        c3_async = _cat_entropy(snaps[2], "async_patterns")
        c4_async = _cat_entropy(snaps[3], "async_patterns")
        assert c4_async - c3_async >= 1

    def test_convention_drift_positive(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        assert snaps[3].divergence.convention_drift_delta is not None
        assert snaps[3].divergence.convention_drift_delta > 0


# ---------------------------------------------------------------------------
# Trend sign sequence [null, +, -, +]
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestTrendSignSequence:
    def test_convention_drift_sign_sequence(self, evolving_shell_repo):
        _, snaps = evolving_shell_repo
        deltas = [s.divergence.convention_drift_delta for s in snaps]
        assert deltas[0] is None
        assert deltas[1] > 0
        assert deltas[2] < 0
        assert deltas[3] > 0

    def test_trend_command_returns_four_points(self, evolving_shell_repo):
        repo_dir, _ = evolving_shell_repo
        runner = CliRunner()
        result = run_sdi(runner, ["trend", "--format", "json"], cwd=repo_dir)
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert len(data.get("snapshots", [])) == 4


# ---------------------------------------------------------------------------
# sdi check exit codes
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestCheckExitCodes:
    def test_c1_to_c2_exits_10(self, evolving_shell_repo):
        """C1→C2 drift exceeds default thresholds → exit 10."""
        _, snaps = evolving_shell_repo
        c2 = snaps[1]
        from sdi.cli.check_cmd import run_checks
        from sdi.config import SDIConfig

        cfg = SDIConfig()
        results = run_checks(c2.divergence, cfg)
        assert any(r.exceeded for r in results)

    def test_c2_to_c3_exits_0(self, evolving_shell_repo):
        """C2→C3 consolidation is within default thresholds → exit 0."""
        _, snaps = evolving_shell_repo
        c3 = snaps[2]
        from sdi.cli.check_cmd import run_checks
        from sdi.config import SDIConfig

        cfg = SDIConfig()
        results = run_checks(c3.divergence, cfg)
        assert not any(r.exceeded for r in results)

    def test_c3_to_c4_exits_0(self, evolving_shell_repo):
        """C3→C4 adds 2 new shapes (< default thresholds) → exit 0."""
        _, snaps = evolving_shell_repo
        c4 = snaps[3]
        from sdi.cli.check_cmd import run_checks
        from sdi.config import SDIConfig

        cfg = SDIConfig()
        results = run_checks(c4.divergence, cfg)
        assert not any(r.exceeded for r in results)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _cat_entropy(snap, category: str) -> int:
    catalog = PatternCatalog.from_dict(snap.pattern_catalog)
    cat = catalog.get_category(category)
    return cat.entropy if cat else 0
