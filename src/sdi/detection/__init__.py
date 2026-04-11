"""Community detection module: Leiden algorithm with partition stability.

Public API:
    detect_communities(graph, config, cache_dir) -> CommunityResult
    CommunityResult: dataclass with partition, stability_score, and metrics
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sdi.detection.leiden import CommunityResult, run_leiden

if TYPE_CHECKING:
    import igraph

    from sdi.config import SDIConfig

__all__ = [
    "CommunityResult",
    "detect_communities",
]


def detect_communities(
    graph: igraph.Graph,
    config: SDIConfig,
    cache_dir: Path,
) -> CommunityResult:
    """Detect structural communities in a dependency graph using Leiden.

    Reads a previous partition from cache_dir/partition.json (warm start) or
    seeds from config.core.random_seed (cold start). Applies a stability
    threshold debounce before reporting cluster assignments. Writes an updated
    cache after every run.

    Args:
        graph: Directed dependency graph produced by build_dependency_graph().
        config: SDI configuration (boundaries.leiden_gamma,
            boundaries.stability_threshold, core.random_seed).
        cache_dir: Directory for the partition cache file. Created if absent.

    Returns:
        CommunityResult with stable partition, stability score, cluster count,
        inter-cluster edge counts, and per-cluster surface area ratios.
    """
    return run_leiden(graph, config, cache_dir)
