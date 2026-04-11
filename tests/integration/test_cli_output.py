"""Integration tests for CLI command output formats and exit codes.

Tests run commands against an initialized SDI project with pre-written
snapshot files. Tree-sitter parsing is NOT invoked — snapshots are
injected directly via write_snapshot().
"""

from __future__ import annotations

import json
from pathlib import Path

from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, Snapshot
from sdi.snapshot.storage import write_snapshot
from tests.conftest import run_sdi


def _write_breach_snapshot(snapshots_dir: Path) -> None:
    """Write a snapshot with a delta that exceeds the default threshold."""
    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-11T10:00:00Z",
        commit_sha=None,
        config_hash="deadbeef01234567",
        divergence=DivergenceSummary(
            pattern_entropy=10.0,
            pattern_entropy_delta=9.0,  # Default threshold is 2.0
            convention_drift=0.1,
            convention_drift_delta=0.0,
            coupling_topology=0.1,
            coupling_topology_delta=0.0,
            boundary_violations=0,
            boundary_violations_delta=0,
        ),
        file_count=5,
        language_breakdown={"python": 5},
    )
    write_snapshot(snap, snapshots_dir)


def _write_two_snapshots(snapshots_dir: Path) -> None:
    """Write two snapshots for diff/trend tests."""
    for ts in ("2026-04-10T10:00:00Z", "2026-04-11T10:00:00Z"):
        snap = Snapshot(
            snapshot_version=SNAPSHOT_VERSION,
            timestamp=ts,
            commit_sha=None,
            config_hash="hash0000",
            divergence=DivergenceSummary(
                pattern_entropy=2.0,
                pattern_entropy_delta=None,
                convention_drift=0.1,
                convention_drift_delta=None,
                coupling_topology=0.2,
                coupling_topology_delta=None,
                boundary_violations=1,
                boundary_violations_delta=None,
            ),
            file_count=5,
            language_breakdown={"python": 5},
        )
        write_snapshot(snap, snapshots_dir)


# ---------------------------------------------------------------------------
# Tests: sdi show
# ---------------------------------------------------------------------------


class TestShowCommand:
    """Tests for `sdi show`."""

    def test_show_text_and_json(self, cli_runner, sdi_project_with_snapshot):
        """Text output includes divergence fields; JSON contains snapshot_version."""
        text = run_sdi(cli_runner, ["show"], sdi_project_with_snapshot)
        assert text.exit_code == 0
        assert "pattern_entropy" in text.output

        js = run_sdi(
            cli_runner, ["--format", "json", "show"], sdi_project_with_snapshot
        )
        assert js.exit_code == 0
        data = json.loads(js.output)
        assert "snapshot_version" in data and "divergence" in data

    def test_show_csv_headers(self, cli_runner, sdi_project_with_snapshot):
        """CSV output has correct headers and four data rows."""
        result = run_sdi(
            cli_runner, ["--format", "csv", "show"], sdi_project_with_snapshot
        )
        assert result.exit_code == 0
        lines = [line for line in result.output.splitlines() if line.strip()]
        assert lines[0] == "dimension,value,delta"
        assert len(lines) == 5  # header + 4 dimension rows

    def test_show_no_snapshots_exits_1(self, cli_runner, sdi_project_dir):
        result = run_sdi(cli_runner, ["show"], sdi_project_dir)
        assert result.exit_code == 1

    def test_show_not_initialized_exits_2(self, cli_runner, git_repo_dir):
        result = run_sdi(cli_runner, ["show"], git_repo_dir)
        assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Tests: sdi diff
# ---------------------------------------------------------------------------


class TestDiffCommand:
    """Tests for `sdi diff`."""

    def test_diff_text_and_json(self, cli_runner, sdi_project_dir):
        """Text diff shows arrow notation; JSON contains snapshot_a/b + divergence."""
        _write_two_snapshots(sdi_project_dir / ".sdi" / "snapshots")

        text = run_sdi(cli_runner, ["diff"], sdi_project_dir)
        assert text.exit_code == 0
        assert "→" in text.output

        js = run_sdi(cli_runner, ["--format", "json", "diff"], sdi_project_dir)
        assert js.exit_code == 0
        data = json.loads(js.output)
        assert "snapshot_a" in data and "snapshot_b" in data and "divergence" in data

    def test_diff_csv_headers(self, cli_runner, sdi_project_dir):
        """CSV diff has dimension/value_b/delta headers."""
        _write_two_snapshots(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["--format", "csv", "diff"], sdi_project_dir)
        assert result.exit_code == 0
        assert result.output.splitlines()[0] == "dimension,value_b,delta"

    def test_diff_one_snapshot_exits_1(self, cli_runner, sdi_project_with_snapshot):
        result = run_sdi(cli_runner, ["diff"], sdi_project_with_snapshot)
        assert result.exit_code == 1

    def test_diff_invalid_ref_a_exits_1(self, cli_runner, sdi_project_dir):
        """diff with a non-existent ref_a exits 1."""
        _write_two_snapshots(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(
            cli_runner, ["diff", "no_such_prefix", "1"], sdi_project_dir
        )
        assert result.exit_code == 1

    def test_diff_invalid_ref_b_exits_1(self, cli_runner, sdi_project_dir):
        """diff with a non-existent ref_b exits 1."""
        _write_two_snapshots(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(
            cli_runner, ["diff", "1", "no_such_prefix"], sdi_project_dir
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Tests: sdi trend
# ---------------------------------------------------------------------------


class TestTrendCommand:
    """Tests for `sdi trend`."""

    def test_trend_no_snapshots_exits_1(self, cli_runner, sdi_project_dir):
        result = run_sdi(cli_runner, ["trend"], sdi_project_dir)
        assert result.exit_code == 1

    def test_trend_json_and_csv(self, cli_runner, sdi_project_with_snapshot):
        """JSON trend has timestamps+dimensions; CSV has timestamp as first column."""
        js = run_sdi(
            cli_runner, ["--format", "json", "trend"], sdi_project_with_snapshot
        )
        assert js.exit_code == 0
        data = json.loads(js.output)
        assert "timestamps" in data and "dimensions" in data

        csv_r = run_sdi(
            cli_runner, ["--format", "csv", "trend"], sdi_project_with_snapshot
        )
        assert csv_r.exit_code == 0
        assert csv_r.output.splitlines()[0].startswith("timestamp")

    def test_trend_invalid_dimension_exits_2(
        self, cli_runner, sdi_project_with_snapshot
    ):
        result = run_sdi(
            cli_runner,
            ["trend", "--dimension", "not_a_real_dimension"],
            sdi_project_with_snapshot,
        )
        assert result.exit_code == 2

    def test_trend_last_n(self, cli_runner, sdi_project_with_snapshot):
        """--last 1 restricts output to one snapshot."""
        result = run_sdi(
            cli_runner, ["--format", "json", "trend", "--last", "1"],
            sdi_project_with_snapshot,
        )
        assert result.exit_code == 0
        assert len(json.loads(result.output)["timestamps"]) == 1


# ---------------------------------------------------------------------------
# Tests: sdi check
# ---------------------------------------------------------------------------


class TestCheckCommand:
    """Tests for `sdi check`."""

    def test_check_null_deltas_ok(self, cli_runner, sdi_project_with_snapshot):
        """First-snapshot null deltas → exits 0 with status=ok."""
        result = run_sdi(cli_runner, ["check"], sdi_project_with_snapshot)
        assert result.exit_code == 0

        js = run_sdi(
            cli_runner, ["--format", "json", "check"], sdi_project_with_snapshot
        )
        assert js.exit_code == 0
        data = json.loads(js.output)
        assert data["status"] == "ok" and len(data["checks"]) == 4

    def test_check_exceeded_exits_10(self, cli_runner, sdi_project_dir):
        """Delta > threshold → exits 10."""
        _write_breach_snapshot(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["check"], sdi_project_dir)
        assert result.exit_code == 10

    def test_check_csv_headers(self, cli_runner, sdi_project_with_snapshot):
        """CSV check output contains dimension and threshold columns."""
        result = run_sdi(
            cli_runner, ["--format", "csv", "check"], sdi_project_with_snapshot
        )
        assert result.exit_code == 0
        header = result.output.splitlines()[0]
        assert "dimension" in header and "threshold" in header


# ---------------------------------------------------------------------------
# Tests: sdi catalog
# ---------------------------------------------------------------------------


class TestCatalogCommand:
    """Tests for `sdi catalog`."""

    def test_catalog_no_data_exits_1(self, cli_runner, sdi_project_with_snapshot):
        """catalog exits 1 when snapshot has no pattern catalog."""
        result = run_sdi(cli_runner, ["catalog"], sdi_project_with_snapshot)
        assert result.exit_code == 1

    def test_catalog_json_with_data(self, cli_runner, sdi_project_dir):
        """catalog returns JSON with catalog data when present."""
        from sdi.patterns.catalog import CategoryStats, PatternCatalog, ShapeStats

        catalog = PatternCatalog(
            categories={
                "error_handling": CategoryStats(
                    name="error_handling",
                    shapes={
                        "abc123": ShapeStats(
                            structural_hash="abc123",
                            instance_count=2,
                            file_paths=["src/a.py"],
                            velocity=None,
                            boundary_spread=None,
                        )
                    },
                )
            }
        )
        snap = Snapshot(
            snapshot_version=SNAPSHOT_VERSION,
            timestamp="2026-04-11T10:00:00Z",
            commit_sha=None,
            config_hash="deadbeef01234567",
            divergence=DivergenceSummary(),
            file_count=1,
            language_breakdown={"python": 1},
            pattern_catalog=catalog.to_dict(),
        )
        write_snapshot(snap, sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(
            cli_runner, ["--format", "json", "catalog"], sdi_project_dir
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "catalog" in data
        assert "error_handling" in data["catalog"]["categories"]
