"""Community detection module: Leiden algorithm with partition stability.

Public API:
    detect_communities(graph, config, cache_dir) -> CommunityResult
    CommunityResult: dataclass with partition, stability_score, and metrics
    BoundarySpec: parsed boundary specification from .sdi/boundaries.yaml
    IntentDivergence: computed violations against a ratified spec
    load_boundary_spec(path) -> BoundarySpec | None
    compute_intent_divergence(spec, partition_data) -> IntentDivergence
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sdi.detection.boundaries import (
    BoundarySpec,
    IntentDivergence,
    compute_intent_divergence,
    load_boundary_spec,
)
from sdi.detection.leiden import CommunityResult, run_leiden

if TYPE_CHECKING:
    import igraph

    from sdi.config import SDIConfig

__all__ = [
    "BoundarySpec",
    "CommunityResult",
    "IntentDivergence",
    "compute_intent_divergence",
    "detect_communities",
    "load_boundary_spec",
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
