"""Unit tests for sdi.snapshot.delta — compute_delta()."""

from __future__ import annotations

import warnings

import pytest

from sdi.snapshot.delta import compute_delta
from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, Snapshot

_INCOMPAT_VERSION = "99.0.0"


def _make_snap(
    pattern_catalog: dict | None = None,
    graph_metrics: dict | None = None,
    partition_data: dict | None = None,
    version: str = SNAPSHOT_VERSION,
) -> Snapshot:
    return Snapshot(
        snapshot_version=version,
        timestamp="2026-04-10T00:00:00Z",
        commit_sha=None,
        config_hash="test",
        divergence=DivergenceSummary(),
        file_count=0,
        language_breakdown={},
        graph_metrics=graph_metrics or {},
        pattern_catalog=pattern_catalog or {},
        partition_data=partition_data or {},
    )


def _catalog(categories: dict[str, list[str]]) -> dict:
    """Minimal serialized PatternCatalog: {category: [hash, ...]}."""
    cats = {}
    for cat_name, hashes in categories.items():
        shapes = {
            h: {
                "structural_hash": h,
                "instance_count": 1,
                "file_paths": ["src/a.py"],
                "velocity": None,
                "boundary_spread": None,
            }
            for h in hashes
        }
        cats[cat_name] = {
            "name": cat_name,
            "entropy": len(hashes),
            "canonical_hash": hashes[0] if hashes else None,
            "shapes": shapes,
        }
    return {"categories": cats}


def _metrics(
    density: float = 0.0,
    hub_concentration: float = 0.0,
    cycle_count: int = 0,
    max_depth: int = 0,
    node_count: int = 10,
) -> dict:
    return {
        "node_count": node_count,
        "edge_count": 0,
        "density": density,
        "cycle_count": cycle_count,
        "hub_concentration": hub_concentration,
        "component_count": 1,
        "max_depth": max_depth,
        "hub_nodes": [],
    }


def _partition(inter_edges: list[dict] | None = None) -> dict:
    return {
        "partition": [0, 1],
        "vertex_names": ["src/a.py", "src/b.py"],
        "inter_cluster_edges": inter_edges or [],
        "cluster_count": 2,
        "stability_score": 1.0,
    }


# ---------------------------------------------------------------------------
# First snapshot: all delta fields are None
# ---------------------------------------------------------------------------


class TestFirstSnapshot:
    """When previous is None, all delta fields must be None."""

    def test_all_deltas_are_none(self) -> None:
        result = compute_delta(_make_snap(), None)
        assert result.pattern_entropy_delta is None
        assert result.convention_drift_delta is None
        assert result.coupling_topology_delta is None
        assert result.boundary_violations_delta is None

    def test_absolute_values_computed(self) -> None:
        snap = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1", "h2"]}))
        result = compute_delta(snap, None)
        assert result.pattern_entropy == 2.0

    def test_returns_divergence_summary(self) -> None:
        assert isinstance(compute_delta(_make_snap(), None), DivergenceSummary)


# ---------------------------------------------------------------------------
# Identical snapshots: all delta fields are zero
# ---------------------------------------------------------------------------


class TestIdenticalSnapshots:
    """When current and previous have identical data, all deltas are zero."""

    def test_entropy_and_drift_deltas_zero(self) -> None:
        snap = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1", "h2"]}))
        result = compute_delta(snap, snap)
        assert result.pattern_entropy_delta == 0.0
        assert result.convention_drift_delta == 0.0

    def test_coupling_and_violation_deltas_zero(self) -> None:
        partition = _partition([{"source_cluster": 0, "target_cluster": 1, "count": 3}])
        snap = _make_snap(
            graph_metrics=_metrics(density=0.3),
            partition_data=partition,
        )
        result = compute_delta(snap, snap)
        assert result.coupling_topology_delta == pytest.approx(0.0)
        assert result.boundary_violations_delta == 0


# ---------------------------------------------------------------------------
# Pattern entropy delta
# ---------------------------------------------------------------------------


class TestPatternEntropyDelta:
    """pattern_entropy_delta = current total distinct shapes - previous total."""

    def test_positive_when_shapes_added(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1", "h2", "h3"]}))
        assert compute_delta(curr, prev).pattern_entropy_delta == pytest.approx(1.0)

    def test_negative_when_shapes_removed(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1", "h2", "h3"]}))
        curr = _make_snap(pattern_catalog=_catalog({"error_handling": ["h1"]}))
        assert compute_delta(curr, prev).pattern_entropy_delta == pytest.approx(-2.0)

    def test_multi_category_entropy_summed(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"cat_a": ["h1"], "cat_b": ["h2"]}))
        curr = _make_snap(
            pattern_catalog=_catalog({"cat_a": ["h1", "h3"], "cat_b": ["h2", "h4"]})
        )
        assert compute_delta(curr, prev).pattern_entropy_delta == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Convention drift delta: new shapes minus lost shapes
# ---------------------------------------------------------------------------


class TestConventionDriftDelta:
    """convention_drift_delta = new shape count - lost shape count."""

    def test_positive_when_shapes_added(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2", "h3"]}))
        # 1 new, 0 lost → +1
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(1.0)

    def test_negative_when_shapes_removed(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2", "h3"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h1"]}))
        # 0 new, 2 lost → -2
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(-2.0)

    def test_zero_net_when_shapes_swap(self) -> None:
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h3", "h4"]}))
        # 2 new, 2 lost → 0
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Coupling topology delta
# ---------------------------------------------------------------------------


class TestCouplingTopologyDelta:
    """coupling_topology_delta = current composite - previous composite."""

    def test_positive_when_metrics_increase(self) -> None:
        prev = _make_snap(graph_metrics=_metrics(density=0.1, hub_concentration=0.1))
        curr = _make_snap(graph_metrics=_metrics(density=0.5, hub_concentration=0.3))
        assert compute_delta(curr, prev).coupling_topology_delta > 0.0

    def test_negative_when_metrics_decrease(self) -> None:
        prev = _make_snap(graph_metrics=_metrics(density=0.5, hub_concentration=0.3))
        curr = _make_snap(graph_metrics=_metrics(density=0.1, hub_concentration=0.0))
        assert compute_delta(curr, prev).coupling_topology_delta < 0.0

    def test_responds_to_cycle_count_and_depth(self) -> None:
        prev = _make_snap(graph_metrics=_metrics(cycle_count=0, max_depth=0, node_count=10))
        curr = _make_snap(graph_metrics=_metrics(cycle_count=5, max_depth=5, node_count=10))
        assert compute_delta(curr, prev).coupling_topology_delta > 0.0


# ---------------------------------------------------------------------------
# Boundary violation velocity
# ---------------------------------------------------------------------------


class TestBoundaryViolationVelocity:
    """boundary_violations_delta = current inter-cluster edges - previous."""

    def test_positive_when_violations_increase(self) -> None:
        prev = _make_snap(
            partition_data=_partition([{"source_cluster": 0, "target_cluster": 1, "count": 2}])
        )
        curr = _make_snap(
            partition_data=_partition(
                [
                    {"source_cluster": 0, "target_cluster": 1, "count": 2},
                    {"source_cluster": 1, "target_cluster": 2, "count": 3},
                ]
            )
        )
        assert compute_delta(curr, prev).boundary_violations_delta == 3

    def test_absolute_value_sums_all_counts(self) -> None:
        partition = _partition(
            [
                {"source_cluster": 0, "target_cluster": 1, "count": 2},
                {"source_cluster": 1, "target_cluster": 2, "count": 3},
            ]
        )
        result = compute_delta(_make_snap(partition_data=partition), None)
        assert result.boundary_violations == 5


# ---------------------------------------------------------------------------
# Incompatible snapshot version: warns and returns None deltas
# ---------------------------------------------------------------------------


class TestIncompatibleVersion:
    """When major versions differ, warn and return None deltas."""

    def test_warning_is_issued(self) -> None:
        curr = _make_snap(version=SNAPSHOT_VERSION)
        prev = _make_snap(version=_INCOMPAT_VERSION)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compute_delta(curr, prev)
        assert len(caught) == 1
        assert issubclass(caught[0].category, UserWarning)
        assert "mismatch" in str(caught[0].message).lower()

    def test_all_deltas_none_on_version_mismatch(self) -> None:
        curr = _make_snap(version=SNAPSHOT_VERSION)
        prev = _make_snap(version=_INCOMPAT_VERSION)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = compute_delta(curr, prev)
        assert result.pattern_entropy_delta is None
        assert result.convention_drift_delta is None
        assert result.coupling_topology_delta is None
        assert result.boundary_violations_delta is None

    def test_absolute_values_computed_despite_mismatch(self) -> None:
        curr = _make_snap(
            pattern_catalog=_catalog({"error_handling": ["h1", "h2"]}),
            version=SNAPSHOT_VERSION,
        )
        prev = _make_snap(version=_INCOMPAT_VERSION)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = compute_delta(curr, prev)
        assert result.pattern_entropy == 2.0
