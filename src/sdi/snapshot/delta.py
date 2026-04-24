"""Delta computation between two SDI snapshots.

Computes all four structural divergence dimensions:
  - pattern_entropy / pattern_entropy_delta
  - convention_drift / convention_drift_delta
  - coupling_topology / coupling_topology_delta
  - boundary_violations / boundary_violations_delta

All delta fields are None when previous is None (first snapshot baseline).
All delta fields are None when snapshot_version major versions differ.
All delta fields are zero when current and previous have identical metrics.
"""

from __future__ import annotations

import warnings
from typing import Any

from sdi.patterns.catalog import PatternCatalog
from sdi.snapshot.model import DivergenceSummary, Snapshot


# ---------------------------------------------------------------------------
# Absolute-value helpers
# ---------------------------------------------------------------------------


def _catalog_pattern_entropy(catalog_dict: dict[str, Any]) -> float:
    """Sum of distinct shape counts across all categories.

    Args:
        catalog_dict: Serialized PatternCatalog dict (from PatternCatalog.to_dict()).

    Returns:
        Total count of distinct structural shapes across all categories.
    """
    if not catalog_dict:
        return 0.0
    catalog = PatternCatalog.from_dict(catalog_dict)
    return float(sum(cat.entropy for cat in catalog.categories.values()))


def _catalog_convention_drift(catalog_dict: dict[str, Any]) -> float:
    """Fraction of non-canonical pattern instances across all categories.

    A value of 0.0 means all code follows the canonical (most common) shape per
    category. A value of 1.0 means no instances match the canonical shape.

    Args:
        catalog_dict: Serialized PatternCatalog dict.

    Returns:
        Non-canonical fraction in [0.0, 1.0], or 0.0 if no instances exist.
    """
    if not catalog_dict:
        return 0.0
    catalog = PatternCatalog.from_dict(catalog_dict)
    total = 0
    non_canonical = 0
    for cat in catalog.categories.values():
        canonical = cat.canonical_hash
        for shape in cat.shapes.values():
            total += shape.instance_count
            if shape.structural_hash != canonical:
                non_canonical += shape.instance_count
    return non_canonical / total if total > 0 else 0.0


def _coupling_composite(metrics: dict[str, Any]) -> float:
    """Normalized composite coupling topology score.

    Averages four normalized sub-metrics: density, hub_concentration,
    cycle_count/node_count, and max_depth/node_count.

    Args:
        metrics: Graph metrics dict from compute_graph_metrics().

    Returns:
        Composite score in [0.0, 1.0]. Returns 0.0 for empty metrics.
    """
    if not metrics:
        return 0.0
    density = float(metrics.get("density", 0.0))
    hub_conc = float(metrics.get("hub_concentration", 0.0))
    n = max(1, int(metrics.get("node_count", 1)))
    cycles = min(1.0, int(metrics.get("cycle_count", 0)) / n)
    depth = min(1.0, int(metrics.get("max_depth", 0)) / n)
    return (density + hub_conc + cycles + depth) / 4.0


def _count_boundary_violations(partition_data: dict[str, Any]) -> int:
    """Total count of cross-boundary violations from partition and intent divergence.

    Combines two measurements:
    - Partition-based: sum of inter-cluster edge counts (structural divergence).
    - Intent-based: total_violations from intent_divergence (spec divergence).

    Args:
        partition_data: Partition info dict stored on a snapshot. May contain
            ``inter_cluster_edges`` and/or ``intent_divergence`` sub-dicts.

    Returns:
        Combined violation count, or 0 if no data.
    """
    edges = partition_data.get("inter_cluster_edges", [])
    partition_count = sum(int(e.get("count", 1)) for e in edges)
    intent_count = int(
        partition_data.get("intent_divergence", {}).get("total_violations", 0)
    )
    return partition_count + intent_count


# ---------------------------------------------------------------------------
# Shape-set helper for convention_drift_delta
# ---------------------------------------------------------------------------


def _shape_set(catalog_dict: dict[str, Any]) -> set[tuple[str, str]]:
    """Return the set of (category_name, structural_hash) pairs in a catalog.

    Args:
        catalog_dict: Serialized PatternCatalog dict.

    Returns:
        Set of (category, hash) tuples — one per distinct shape.
    """
    if not catalog_dict:
        return set()
    catalog = PatternCatalog.from_dict(catalog_dict)
    result: set[tuple[str, str]] = set()
    for cat_name, cat in catalog.categories.items():
        for hash_val in cat.shapes:
            result.add((cat_name, hash_val))
    return result


# ---------------------------------------------------------------------------
# Version compatibility
# ---------------------------------------------------------------------------


def _major_version(snap: Snapshot) -> str:
    """Extract the major version component from a snapshot's version string."""
    return snap.snapshot_version.split(".")[0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_delta(
    current: Snapshot,
    previous: Snapshot | None,
) -> DivergenceSummary:
    """Compute a DivergenceSummary for *current* against *previous*.

    Absolute values (pattern_entropy, convention_drift, coupling_topology,
    boundary_violations) are always computed from *current*. Delta fields are
    None on the first snapshot or when versions are incompatible.

    Args:
        current: The snapshot being measured.
        previous: The baseline snapshot to diff against. Pass None for the
            first snapshot — all delta fields will be None.

    Returns:
        DivergenceSummary with absolute values and delta fields populated.
        Delta fields are None when previous is None or incompatible.
        Delta fields are zero when current and previous have identical data.
    """
    pattern_entropy = _catalog_pattern_entropy(current.pattern_catalog)
    convention_drift = _catalog_convention_drift(current.pattern_catalog)
    coupling_topology = _coupling_composite(current.graph_metrics)
    boundary_violations = _count_boundary_violations(current.partition_data)

    if previous is None:
        return DivergenceSummary(
            pattern_entropy=pattern_entropy,
            pattern_entropy_delta=None,
            convention_drift=convention_drift,
            convention_drift_delta=None,
            coupling_topology=coupling_topology,
            coupling_topology_delta=None,
            boundary_violations=boundary_violations,
            boundary_violations_delta=None,
        )

    if _major_version(current) != _major_version(previous):
        warnings.warn(
            f"Snapshot version mismatch: {current.snapshot_version!r} vs "
            f"{previous.snapshot_version!r}. No delta computed.",
            UserWarning,
            stacklevel=2,
        )
        return DivergenceSummary(
            pattern_entropy=pattern_entropy,
            pattern_entropy_delta=None,
            convention_drift=convention_drift,
            convention_drift_delta=None,
            coupling_topology=coupling_topology,
            coupling_topology_delta=None,
            boundary_violations=boundary_violations,
            boundary_violations_delta=None,
        )

    prev_entropy = _catalog_pattern_entropy(previous.pattern_catalog)
    prev_coupling = _coupling_composite(previous.graph_metrics)
    prev_violations = _count_boundary_violations(previous.partition_data)

    curr_shapes = _shape_set(current.pattern_catalog)
    prev_shapes = _shape_set(previous.pattern_catalog)
    new_shapes = len(curr_shapes - prev_shapes)
    lost_shapes = len(prev_shapes - curr_shapes)

    return DivergenceSummary(
        pattern_entropy=pattern_entropy,
        pattern_entropy_delta=pattern_entropy - prev_entropy,
        convention_drift=convention_drift,
        convention_drift_delta=float(new_shapes - lost_shapes),
        coupling_topology=coupling_topology,
        coupling_topology_delta=coupling_topology - prev_coupling,
        boundary_violations=boundary_violations,
        boundary_violations_delta=boundary_violations - prev_violations,
    )
