"""Unit tests for sdi.snapshot.trend — compute_trend(), TrendData."""

from __future__ import annotations

import pytest

from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, Snapshot
from sdi.snapshot.trend import ALL_DIMENSIONS, TrendData, compute_trend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snap(
    timestamp: str,
    pattern_entropy: float | None = None,
    pattern_entropy_delta: float | None = None,
    convention_drift: float | None = None,
    convention_drift_delta: float | None = None,
    coupling_topology: float | None = None,
    coupling_topology_delta: float | None = None,
    boundary_violations: int | None = None,
    boundary_violations_delta: int | None = None,
) -> Snapshot:
    """Build a Snapshot with explicit divergence field values."""
    divergence = DivergenceSummary(
        pattern_entropy=pattern_entropy,
        pattern_entropy_delta=pattern_entropy_delta,
        convention_drift=convention_drift,
        convention_drift_delta=convention_drift_delta,
        coupling_topology=coupling_topology,
        coupling_topology_delta=coupling_topology_delta,
        boundary_violations=boundary_violations,
        boundary_violations_delta=boundary_violations_delta,
    )
    return Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp=timestamp,
        commit_sha=None,
        config_hash="test",
        divergence=divergence,
        file_count=0,
        language_breakdown={},
    )


def _five_snapshots() -> list[Snapshot]:
    """Return five snapshots with deterministic divergence values."""
    return [
        _make_snap(
            "2026-04-01T00:00:00Z",
            pattern_entropy=3.0, pattern_entropy_delta=None,  # first snapshot
            convention_drift=0.1, convention_drift_delta=None,
            coupling_topology=0.2, coupling_topology_delta=None,
            boundary_violations=2, boundary_violations_delta=None,
        ),
        _make_snap(
            "2026-04-02T00:00:00Z",
            pattern_entropy=4.0, pattern_entropy_delta=1.0,
            convention_drift=0.2, convention_drift_delta=1.0,
            coupling_topology=0.3, coupling_topology_delta=0.1,
            boundary_violations=3, boundary_violations_delta=1,
        ),
        _make_snap(
            "2026-04-03T00:00:00Z",
            pattern_entropy=4.0, pattern_entropy_delta=0.0,
            convention_drift=0.2, convention_drift_delta=0.0,
            coupling_topology=0.3, coupling_topology_delta=0.0,
            boundary_violations=3, boundary_violations_delta=0,
        ),
        _make_snap(
            "2026-04-04T00:00:00Z",
            pattern_entropy=6.0, pattern_entropy_delta=2.0,
            convention_drift=0.4, convention_drift_delta=2.0,
            coupling_topology=0.5, coupling_topology_delta=0.2,
            boundary_violations=5, boundary_violations_delta=2,
        ),
        _make_snap(
            "2026-04-05T00:00:00Z",
            pattern_entropy=5.0, pattern_entropy_delta=-1.0,
            convention_drift=0.3, convention_drift_delta=-1.0,
            coupling_topology=0.4, coupling_topology_delta=-0.1,
            boundary_violations=4, boundary_violations_delta=-1,
        ),
    ]


# ---------------------------------------------------------------------------
# Tests: basic structure
# ---------------------------------------------------------------------------


class TestTrendDataStructure:
    """TrendData has correct structure and types."""

    def test_returns_trend_data_instance(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps)
        assert isinstance(result, TrendData)

    def test_timestamps_match_snapshot_order(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps)
        expected = [s.timestamp for s in snaps]
        assert result.timestamps == expected

    def test_dimension_list_length_matches_snapshot_count(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta"])
        assert len(result.dimensions["pattern_entropy_delta"]) == 5

    def test_empty_snapshots_list(self) -> None:
        result = compute_trend([])
        assert result.timestamps == []
        assert all(v == [] for v in result.dimensions.values())


# ---------------------------------------------------------------------------
# Tests: five-snapshot time series correctness
# ---------------------------------------------------------------------------


class TestFiveSnapshotTrend:
    """Trend across five snapshots produces correct ordered series."""

    def test_pattern_entropy_delta_series(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta"])
        assert result.dimensions["pattern_entropy_delta"] == [
            None, 1.0, 0.0, 2.0, -1.0
        ]

    def test_first_entry_is_null_for_delta_dimension(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["convention_drift_delta"])
        assert result.dimensions["convention_drift_delta"][0] is None

    def test_boundary_violations_delta_converted_to_float(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["boundary_violations_delta"])
        series = result.dimensions["boundary_violations_delta"]
        # All non-None values must be float
        for val in series:
            if val is not None:
                assert isinstance(val, float)

    def test_all_dimensions_present_by_default(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps)
        for dim in ALL_DIMENSIONS:
            assert dim in result.dimensions


# ---------------------------------------------------------------------------
# Tests: dimension filter
# ---------------------------------------------------------------------------


class TestDimensionFilter:
    """Dimension filter limits output to requested dimensions only."""

    def test_single_dimension_only(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta"])
        assert list(result.dimensions.keys()) == ["pattern_entropy_delta"]

    def test_two_dimensions(self) -> None:
        snaps = _five_snapshots()
        dims = ["pattern_entropy_delta", "coupling_topology_delta"]
        result = compute_trend(snaps, dims)
        assert set(result.dimensions.keys()) == set(dims)

    def test_unknown_dimension_silently_omitted(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta", "nonexistent_dim"])
        assert "nonexistent_dim" not in result.dimensions
        assert "pattern_entropy_delta" in result.dimensions


# ---------------------------------------------------------------------------
# Tests: single snapshot (baseline only)
# ---------------------------------------------------------------------------


class TestSingleSnapshotBaseline:
    """Single snapshot has null deltas and non-null absolute values."""

    def test_delta_is_none_for_single_snapshot(self) -> None:
        snap = _make_snap(
            "2026-04-01T00:00:00Z",
            pattern_entropy=3.0, pattern_entropy_delta=None,
        )
        result = compute_trend([snap], ["pattern_entropy_delta"])
        assert result.dimensions["pattern_entropy_delta"] == [None]

    def test_absolute_value_present_for_single_snapshot(self) -> None:
        snap = _make_snap(
            "2026-04-01T00:00:00Z",
            pattern_entropy=3.0, pattern_entropy_delta=None,
        )
        result = compute_trend([snap], ["pattern_entropy"])
        assert result.dimensions["pattern_entropy"] == [3.0]


# ---------------------------------------------------------------------------
# Tests: to_dict serialization
# ---------------------------------------------------------------------------


class TestTrendDataSerialization:
    """TrendData serializes to a dict correctly."""

    def test_to_dict_has_timestamps(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta"])
        d = result.to_dict()
        assert "timestamps" in d
        assert len(d["timestamps"]) == 5

    def test_to_dict_has_dimensions(self) -> None:
        snaps = _five_snapshots()
        result = compute_trend(snaps, ["pattern_entropy_delta"])
        d = result.to_dict()
        assert "dimensions" in d
        assert "pattern_entropy_delta" in d["dimensions"]
