"""Unit tests for sdi.snapshot.delta — compute_delta() and _count_boundary_violations()."""

from __future__ import annotations

import warnings

import pytest

from sdi.snapshot.delta import _count_boundary_violations, compute_delta
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
        curr = _make_snap(pattern_catalog=_catalog({"cat_a": ["h1", "h3"], "cat_b": ["h2", "h4"]}))
        assert compute_delta(curr, prev).pattern_entropy_delta == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Convention drift delta: change in non-canonical instance fraction
# ---------------------------------------------------------------------------


class TestConventionDriftDelta:
    """convention_drift_delta = current_drift_fraction - previous_drift_fraction.

    Both the absolute value and the delta are expressed in the same units
    (non-canonical fraction in [0.0, 1.0]), so Value + Δ ≈ NewValue.
    """

    def test_positive_when_drift_increases(self) -> None:
        # prev: 1/2 non-canonical = 0.5; curr: 2/3 non-canonical ≈ 0.667 → +0.167
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2", "h3"]}))
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(2 / 3 - 1 / 2)

    def test_negative_when_drift_decreases(self) -> None:
        # prev: 2/3 non-canonical ≈ 0.667; curr: 0/1 = 0.0 → -0.667
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2", "h3"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h1"]}))
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(-2 / 3)

    def test_zero_when_fraction_unchanged(self) -> None:
        # Swapping shapes 1:1 keeps non-canonical fraction at 1/2 → delta 0.0
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h3", "h4"]}))
        assert compute_delta(curr, prev).convention_drift_delta == pytest.approx(0.0)

    def test_value_plus_delta_equals_new_value(self) -> None:
        # The arithmetic identity that motivated the unit fix.
        prev = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2"]}))
        curr = _make_snap(pattern_catalog=_catalog({"eh": ["h1", "h2", "h3", "h4"]}))
        result = compute_delta(curr, prev)
        prev_value = compute_delta(prev, None).convention_drift
        assert prev_value + result.convention_drift_delta == pytest.approx(result.convention_drift)


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
        prev = _make_snap(partition_data=_partition([{"source_cluster": 0, "target_cluster": 1, "count": 2}]))
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
# _count_boundary_violations: M9 addition — includes intent_divergence
# ---------------------------------------------------------------------------


class TestCountBoundaryViolationsIntentDivergence:
    """_count_boundary_violations combines inter-cluster edges AND intent violations."""

    def test_intent_divergence_total_violations_added_to_partition_count(self) -> None:
        """Intent divergence violations are added on top of inter-cluster edge counts."""
        pd = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [{"source_cluster": 0, "target_cluster": 1, "count": 3}],
            "cluster_count": 2,
            "stability_score": 1.0,
            "intent_divergence": {"total_violations": 4},
        }
        assert _count_boundary_violations(pd) == 7  # 3 + 4

    def test_intent_divergence_alone_without_inter_cluster_edges(self) -> None:
        """Intent violations count when there are no inter-cluster edges."""
        pd = {
            "partition": [0],
            "vertex_names": ["src/a.py"],
            "inter_cluster_edges": [],
            "cluster_count": 1,
            "stability_score": 1.0,
            "intent_divergence": {"total_violations": 5},
        }
        assert _count_boundary_violations(pd) == 5

    def test_zero_intent_violations_does_not_change_partition_count(self) -> None:
        """A zero total_violations in intent_divergence leaves the edge count unchanged."""
        pd = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [{"source_cluster": 0, "target_cluster": 1, "count": 2}],
            "cluster_count": 2,
            "stability_score": 1.0,
            "intent_divergence": {"total_violations": 0},
        }
        assert _count_boundary_violations(pd) == 2

    def test_missing_intent_divergence_key_returns_only_edge_count(self) -> None:
        """Absence of intent_divergence in partition_data is not an error."""
        pd = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [{"source_cluster": 0, "target_cluster": 1, "count": 6}],
            "cluster_count": 2,
            "stability_score": 1.0,
        }
        assert _count_boundary_violations(pd) == 6

    def test_both_intent_and_edges_are_additive(self) -> None:
        """Verifies the two sources are strictly additive, not de-duplicated."""
        pd = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [
                {"source_cluster": 0, "target_cluster": 1, "count": 2},
                {"source_cluster": 1, "target_cluster": 0, "count": 1},
            ],
            "cluster_count": 2,
            "stability_score": 1.0,
            "intent_divergence": {"total_violations": 10},
        }
        assert _count_boundary_violations(pd) == 13  # 2 + 1 + 10

    def test_empty_partition_data_returns_zero(self) -> None:
        assert _count_boundary_violations({}) == 0

    def test_intent_divergence_with_snapshot_compute_delta_integration(self) -> None:
        """boundary_violations on a snapshot with intent_divergence includes those violations."""
        pd = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [{"source_cluster": 0, "target_cluster": 1, "count": 2}],
            "cluster_count": 2,
            "stability_score": 1.0,
            "intent_divergence": {"total_violations": 3},
        }
        snap = _make_snap(partition_data=pd)
        result = compute_delta(snap, None)
        assert result.boundary_violations == 5  # 2 + 3


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
