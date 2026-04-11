"""Leiden community detection with partition stability and debounce.

Wraps leidenalg.find_partition() with:
  - Cold-start seeding from config.random_seed
  - Warm-start seeding from cached stable partition (read from cache_dir)
  - Stability threshold debounce via _partition_cache helpers
  - Atomic partition cache write after every run

Cache helpers, debounce logic, and stability scoring live in _partition_cache.py.
"""

from __future__ import annotations

import logging
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sdi.detection._partition_cache import (
    PARTITION_CACHE_VERSION,
    _apply_debounce,
    _build_initial_membership,
    _compute_stability_score,
    _read_cache,
    _write_cache,
)

try:
    import igraph
except ImportError:
    print(
        "[error] igraph is required for community detection. "
        "Install with: pip install igraph",
        file=sys.stderr,
    )
    raise

try:
    import leidenalg
except ImportError:
    print(
        "[error] leidenalg is required for community detection. "
        "Install with: pip install leidenalg",
        file=sys.stderr,
    )
    raise

if TYPE_CHECKING:
    from sdi.config import SDIConfig

logger = logging.getLogger(__name__)

_TRIVIAL_GRAPH_THRESHOLD = 10  # graphs with fewer nodes return a trivial partition


@dataclass
class CommunityResult:
    """Result of one Leiden community detection run.

    Args:
        partition: Cluster assignment per vertex (index = igraph vertex id).
        stability_score: Fraction of nodes retaining stable cluster membership
            since the previous run. 1.0 on cold start or unchanged graph.
        cluster_count: Number of distinct clusters detected.
        inter_cluster_edges: Directed edge counts between distinct clusters.
            Each entry: {"source_cluster": int, "target_cluster": int, "count": int}.
        surface_area_ratios: Per-cluster ratio of boundary-crossing edges to
            total edges touching that cluster. Dict keyed by cluster id.
        vertex_names: Ordered list of vertex names (file paths) corresponding
            to partition indices. Index i → partition[i] = cluster id.
    """

    partition: list[int]
    stability_score: float
    cluster_count: int
    inter_cluster_edges: list[dict[str, int]]
    surface_area_ratios: dict[int, float]
    vertex_names: list[str]


def _compute_inter_cluster_edges(
    graph: igraph.Graph, partition: list[int]
) -> list[dict[str, int]]:
    """Compute directed edge counts between distinct clusters.

    Args:
        graph: Dependency graph.
        partition: Stable cluster assignment per vertex.

    Returns:
        List of dicts with keys source_cluster, target_cluster, count.
        Sorted by (source_cluster, target_cluster).
    """
    counts: dict[tuple[int, int], int] = {}
    for edge in graph.es:
        sc = partition[edge.source]
        tc = partition[edge.target]
        if sc != tc:
            key = (sc, tc)
            counts[key] = counts.get(key, 0) + 1
    return [
        {"source_cluster": s, "target_cluster": t, "count": c}
        for (s, t), c in sorted(counts.items())
    ]


def _compute_surface_area_ratios(
    graph: igraph.Graph,
    partition: list[int],
) -> dict[int, float]:
    """Compute fraction of boundary-crossing edges per cluster.

    Surface area ratio for cluster C = external_edges(C) / total_edges(C).
    Internal edges count once for their cluster; external edges count once
    for each cluster they touch.

    Args:
        graph: Dependency graph.
        partition: Stable cluster assignment per vertex.

    Returns:
        Dict mapping cluster id → surface area ratio in [0.0, 1.0].
        Keys are the actual cluster IDs present in partition (not range-based).
    """
    cluster_ids = set(partition)
    total: dict[int, int] = {c: 0 for c in cluster_ids}
    external: dict[int, int] = {c: 0 for c in cluster_ids}

    for edge in graph.es:
        sc = partition[edge.source]
        tc = partition[edge.target]
        if sc == tc:
            total[sc] = total.get(sc, 0) + 1
        else:
            total[sc] = total.get(sc, 0) + 1
            total[tc] = total.get(tc, 0) + 1
            external[sc] = external.get(sc, 0) + 1
            external[tc] = external.get(tc, 0) + 1

    return {
        c: external.get(c, 0) / total[c] if total.get(c, 0) > 0 else 0.0
        for c in cluster_ids
    }


def run_leiden(
    graph: igraph.Graph,
    config: SDIConfig,
    cache_dir: Path,
) -> CommunityResult:
    """Run Leiden community detection with stability debounce and caching.

    On cold start (no cache), seeds from config.core.random_seed for
    reproducibility. On warm start, seeds from the previous stable partition
    and applies the stability threshold debounce before updating the cache.

    Args:
        graph: Directed dependency graph from Stage 2.
        config: SDI configuration (boundaries.leiden_gamma,
            boundaries.stability_threshold, core.random_seed).
        cache_dir: Directory for reading/writing partition.json.

    Returns:
        CommunityResult with stable partition, stability score, and metrics.
    """
    n = graph.vcount()
    vertex_names: list[str] = (
        graph.vs["name"]
        if "name" in graph.vertex_attributes()
        else [str(i) for i in range(n)]
    )

    if n < _TRIVIAL_GRAPH_THRESHOLD:
        warnings.warn(
            "insufficient structure for boundary detection "
            f"(graph has {n} nodes; minimum is {_TRIVIAL_GRAPH_THRESHOLD})",
            stacklevel=2,
        )
        trivial = [0] * n
        cluster_count = 1 if n > 0 else 0
        ratios: dict[int, float] = {0: 0.0} if n > 0 else {}
        return CommunityResult(
            partition=trivial,
            stability_score=1.0,
            cluster_count=cluster_count,
            inter_cluster_edges=[],
            surface_area_ratios=ratios,
            vertex_names=vertex_names,
        )

    gamma: float = config.boundaries.leiden_gamma
    threshold: int = config.boundaries.stability_threshold
    seed: int = config.core.random_seed

    prev_cache = _read_cache(cache_dir)

    if prev_cache is not None:
        initial_membership = _build_initial_membership(graph, prev_cache)
        logger.debug("Warm-start Leiden from cached partition (seed=%d)", seed)
    else:
        initial_membership = None
        logger.debug("Cold-start Leiden (seed=%d)", seed)

    lpart = leidenalg.find_partition(
        graph,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=gamma,
        seed=seed,
        initial_membership=initial_membership,
    )
    raw_partition: list[int] = list(lpart.membership)

    stable_partition, node_history = _apply_debounce(
        vertex_names, raw_partition, prev_cache, threshold
    )
    stability_score = _compute_stability_score(prev_cache, stable_partition, vertex_names)
    cluster_count = len(set(stable_partition)) if stable_partition else 0

    _write_cache(
        cache_dir,
        {
            "cache_version": PARTITION_CACHE_VERSION,
            "vertex_names": vertex_names,
            "stable_partition": stable_partition,
            "node_history": node_history,
        },
    )

    return CommunityResult(
        partition=stable_partition,
        stability_score=stability_score,
        cluster_count=cluster_count,
        inter_cluster_edges=_compute_inter_cluster_edges(graph, stable_partition),
        surface_area_ratios=_compute_surface_area_ratios(graph, stable_partition),
        vertex_names=vertex_names,
    )
