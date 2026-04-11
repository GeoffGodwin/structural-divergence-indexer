"""Graph metric computation for dependency analysis.

Computes structural metrics over an igraph.Graph: density, cycle count,
hub concentration, connected component count, and maximum dependency depth.
These metrics are included in snapshot JSON and must have stable key names.
"""

from __future__ import annotations

import math
import sys
from typing import Any

try:
    import igraph
except ImportError:
    print(
        "[error] igraph is required for graph metrics. "
        "Install with: pip install igraph",
        file=sys.stderr,
    )
    raise

# Nodes with in-degree >= this threshold are considered hubs.
HUB_INDEGREE_THRESHOLD = 3


def _compute_max_depth(graph: igraph.Graph) -> int:
    """Compute the maximum dependency depth (graph diameter).

    For a DAG this equals the longest chain from any root to any reachable
    leaf. For graphs with cycles it equals the longest shortest path between
    any pair of vertices (graph diameter).

    Args:
        graph: Directed dependency graph.

    Returns:
        Maximum dependency depth as an integer. Returns 0 for graphs with
        no edges or a single node.
    """
    if graph.vcount() == 0 or graph.ecount() == 0:
        return 0

    diameter = graph.diameter(directed=True)

    # diameter returns nan/inf for empty or fully-disconnected graphs
    if diameter is None or math.isnan(diameter) or math.isinf(diameter):
        return 0

    return int(diameter)


def _compute_hub_info(
    graph: igraph.Graph,
) -> tuple[float, list[str]]:
    """Compute hub concentration and hub node list.

    Hubs are nodes whose in-degree meets or exceeds HUB_INDEGREE_THRESHOLD.
    Returns (0.0, []) for graphs with fewer than 3 nodes.

    Args:
        graph: Directed dependency graph with vertex attribute "name".

    Returns:
        Tuple of (hub_concentration: float in [0.0, 1.0], hub_nodes: list[str]).
    """
    n = graph.vcount()
    if n < 3:
        return 0.0, []

    indegrees = graph.indegree()
    names: list[str]
    if "name" in graph.vertex_attributes():
        names = graph.vs["name"]
    else:
        names = [str(i) for i in range(n)]

    hub_nodes = [
        names[i] for i, d in enumerate(indegrees) if d >= HUB_INDEGREE_THRESHOLD
    ]
    hub_concentration = len(hub_nodes) / n
    return hub_concentration, hub_nodes


def compute_graph_metrics(graph: igraph.Graph) -> dict[str, Any]:
    """Compute structural metrics for a dependency graph.

    All returned keys are part of the snapshot JSON schema and must not
    be renamed without a schema version bump.

    Args:
        graph: Directed dependency graph built by build_dependency_graph().

    Returns:
        Dict with keys:
            node_count (int): Number of vertices.
            edge_count (int): Number of directed edges.
            density (float): Graph density in [0.0, 1.0].
            cycle_count (int): Number of simple cycles.
            hub_concentration (float): Ratio of hub nodes to total nodes.
            hub_nodes (list[str]): File paths of hub nodes.
            component_count (int): Number of weakly-connected components.
            max_depth (int): Maximum dependency chain length (graph diameter).
    """
    n = graph.vcount()
    e = graph.ecount()

    # Basic counts
    node_count = n
    edge_count = e

    # Density: 0.0 for graphs too small to have directed edges
    if n < 2:
        density = 0.0
    else:
        raw_density = graph.density()
        if raw_density is None or math.isnan(raw_density):
            density = 0.0
        else:
            density = raw_density

    # Cycle count: simple directed cycles
    if n == 0:
        cycle_count = 0
    else:
        cycle_count = len(graph.simple_cycles())

    # Weakly-connected component count
    if n == 0:
        component_count = 0
    else:
        component_count = len(graph.connected_components(mode="weak"))

    # Hub concentration and hub nodes
    hub_concentration, hub_nodes = _compute_hub_info(graph)

    # Maximum dependency depth
    max_depth = _compute_max_depth(graph)

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "cycle_count": cycle_count,
        "hub_concentration": hub_concentration,
        "hub_nodes": hub_nodes,
        "component_count": component_count,
        "max_depth": max_depth,
    }
