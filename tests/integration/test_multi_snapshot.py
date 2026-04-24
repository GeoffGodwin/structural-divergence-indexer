"""Full lifecycle integration tests on an evolving fixture.

Tests: init → snapshot (null-delta baseline) → add drift files →
       snapshot (with computed deltas) → diff → trend (two-point) →
       check (tight thresholds → exit 10, relaxed → exit 0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdi.snapshot.storage import list_snapshots, read_snapshot
from tests.conftest import requires_python_adapter, run_sdi
from tests.fixtures.setup_fixture import create_evolving_fixture


def _latest_by_mtime(snaps_dir: Path) -> Path:
    """Return the most recently written snapshot file using mtime.

    Sorts by mtime_ns rather than filename so that two snapshots captured
    within the same wall-clock second are still correctly ordered.

    # TODO: remove once list_snapshots uses mtime ordering natively.

    Args:
        snaps_dir: Directory containing snapshot JSON files.

    Returns:
        Path to the snapshot file with the highest mtime_ns.

    Raises:
        FileNotFoundError: If no snapshots exist in snaps_dir.
    """
    paths = list_snapshots(snaps_dir)
    if not paths:
        raise FileNotFoundError(f"No snapshots found in {snaps_dir}")
    return max(paths, key=lambda p: p.stat().st_mtime_ns)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def evolving_project(tmp_path: Path) -> Path:
    """Temp git repo with 5 commits of progressive structural drift."""
    repo = tmp_path / "evolving"
    create_evolving_fixture(repo)
    sdi_dir = repo / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    return repo


def _add_drift_files(repo: Path) -> None:
    """Write new files with structurally distinct error-handling patterns.

    These patterns are chosen to produce at least one new structural hash
    not present in the baseline fixture, ensuring a measurable delta.
    """
    (repo / "drift_a.py").write_text(
        "def decode(data: bytes) -> str:\n"
        "    try:\n"
        "        return data.decode('utf-8')\n"
        "    except (UnicodeDecodeError, AttributeError, ValueError):\n"
        "        return ''\n",
        encoding="utf-8",
    )
    (repo / "drift_b.py").write_text(
        "def safe_open(path: str) -> object:\n"
        "    try:\n"
        "        return open(path)\n"
        "    except FileNotFoundError:\n"
        "        return None\n"
        "    except PermissionError:\n"
        "        raise\n"
        "    except OSError as exc:\n"
        "        raise RuntimeError('io error') from exc\n",
        encoding="utf-8",
    )
    (repo / "drift_c.py").write_text(
        "import logging\n\n"
        "log = logging.getLogger('drift')\n\n"
        "def notify(event: str) -> None:\n"
        "    log.debug(event)\n"
        "    log.info('received: %s', event)\n"
        "    log.warning('check: %s', event)\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_python_adapter
class TestMultiSnapshotLifecycle:
    """Full init → snapshot → modify → snapshot → diff → trend → check lifecycle."""

    def test_first_snapshot_has_null_deltas(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """First snapshot baseline must have null deltas in all dimensions."""
        result = run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        assert result.exit_code == 0, result.output

        js = run_sdi(cli_runner, ["--format", "json", "show"], evolving_project)
        assert js.exit_code == 0
        div = json.loads(js.output)["divergence"]
        assert div["pattern_entropy_delta"] is None
        assert div["convention_drift_delta"] is None
        assert div["coupling_topology_delta"] is None
        assert div["boundary_violations_delta"] is None

    def test_second_snapshot_has_non_null_deltas(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """Second snapshot after adding drift files has non-null deltas.

        Reads the second snapshot directly by mtime (rather than via `sdi show`)
        so the assertion is not affected by filename-sort order when both
        snapshots share the same second-level timestamp.
        """
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        result = run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        assert result.exit_code == 0, result.output

        snaps_dir = evolving_project / ".sdi" / "snapshots"
        snap2 = read_snapshot(_latest_by_mtime(snaps_dir))
        assert snap2.divergence.pattern_entropy_delta is not None
        assert snap2.divergence.convention_drift_delta is not None

    def test_diff_text_shows_arrow(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """diff command text output contains the → arrow between snapshots."""
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(cli_runner, ["diff"], evolving_project)
        assert result.exit_code == 0
        assert "→" in result.output

    def test_diff_json_structure(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """diff --format json has snapshot_a, snapshot_b, and divergence keys."""
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(cli_runner, ["--format", "json", "diff"], evolving_project)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "snapshot_a" in data
        assert "snapshot_b" in data
        assert "divergence" in data

    def test_trend_returns_two_data_points(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """trend after two snapshots returns exactly two timestamps."""
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(
            cli_runner, ["--format", "json", "trend"], evolving_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["timestamps"]) == 2

    def test_trend_csv_starts_with_timestamp(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """trend --format csv first column is timestamp."""
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(
            cli_runner, ["--format", "csv", "trend"], evolving_project
        )
        assert result.exit_code == 0
        assert result.output.splitlines()[0].startswith("timestamp")

    def test_check_relaxed_thresholds_exits_0(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """check with very relaxed thresholds exits 0 after drift."""
        (evolving_project / ".sdi" / "config.toml").write_text(
            "[thresholds]\n"
            "pattern_entropy_rate = 999.0\n"
            "convention_drift_rate = 999.0\n"
            "coupling_delta_rate = 999.0\n"
            "boundary_violation_rate = 999.0\n",
            encoding="utf-8",
        )
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(cli_runner, ["check"], evolving_project)
        assert result.exit_code == 0

    def test_check_tight_thresholds_exits_10(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """check exits 10 when the drift snapshot has deltas exceeding tight thresholds.

        After both snapshots are taken the second snapshot is identified by mtime
        and its stem is passed as an explicit ref so that sdi check reads it
        regardless of alphabetical filename sort order.
        """
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        _add_drift_files(evolving_project)
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        snaps_dir = evolving_project / ".sdi" / "snapshots"
        snap2_ref = _latest_by_mtime(snaps_dir).stem  # filename without .json

        # config.toml is written after both snapshots because thresholds are
        # only evaluated by `sdi check`, not at snapshot capture time.
        (evolving_project / ".sdi" / "config.toml").write_text(
            "[thresholds]\n"
            "pattern_entropy_rate = 0.001\n"
            "convention_drift_rate = 0.001\n"
            "coupling_delta_rate = 0.001\n"
            "boundary_violation_rate = 0.001\n",
            encoding="utf-8",
        )
        result = run_sdi(cli_runner, ["check", snap2_ref], evolving_project)
        assert result.exit_code == 10

    def test_check_json_output_structure(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """check --format json returns status and checks list."""
        run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)

        result = run_sdi(
            cli_runner, ["--format", "json", "check"], evolving_project
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "status" in data
        assert "checks" in data
        assert len(data["checks"]) == 4


# ---------------------------------------------------------------------------
# sdi boundaries command tests
# ---------------------------------------------------------------------------


@requires_python_adapter
class TestBoundariesCommand:
    """sdi boundaries command in the multi-snapshot lifecycle."""

    def test_boundaries_show_no_spec_exits_0(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """sdi boundaries with no boundaries.yaml exits 0 and reports absence."""
        result = run_sdi(cli_runner, ["boundaries"], evolving_project)
        assert result.exit_code == 0, result.output
        assert "No boundary spec found" in result.output

    def test_boundaries_propose_exits_1_without_snapshot(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """sdi boundaries --propose exits 1 when no snapshots have been taken yet."""
        result = run_sdi(
            cli_runner, ["boundaries", "--propose"], evolving_project
        )
        assert result.exit_code == 1

    def test_boundaries_propose_after_snapshot_shows_yaml(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """sdi boundaries --propose after a snapshot outputs a proposed YAML spec."""
        snap_result = run_sdi(cli_runner, ["-q", "snapshot"], evolving_project)
        assert snap_result.exit_code == 0, snap_result.output

        result = run_sdi(
            cli_runner, ["boundaries", "--propose"], evolving_project
        )
        assert result.exit_code == 0, result.output
        assert "sdi_boundaries:" in result.output
        assert "modules:" in result.output

    def test_boundaries_show_with_spec_file(
        self, cli_runner: object, evolving_project: Path
    ) -> None:
        """sdi boundaries with a valid boundaries.yaml displays the module listing."""
        spec_content = (
            "sdi_boundaries:\n"
            '  version: "0.1.0"\n'
            '  generated_from: "manual"\n'
            "  modules:\n"
            "    - name: core\n"
            "      paths:\n"
            "        - src/core/\n"
            "  allowed_cross_domain: []\n"
            "  aspirational_splits: []\n"
        )
        spec_path = evolving_project / ".sdi" / "boundaries.yaml"
        spec_path.write_text(spec_content, encoding="utf-8")

        result = run_sdi(cli_runner, ["boundaries"], evolving_project)
        assert result.exit_code == 0, result.output
        assert "Modules" in result.output
        assert "core" in result.output
