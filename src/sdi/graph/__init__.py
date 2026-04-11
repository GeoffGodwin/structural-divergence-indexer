"""Dependency graph module: construction and metrics.

Public API:
    build_dependency_graph(records, config) -> tuple[igraph.Graph, dict]
    compute_graph_metrics(graph) -> dict
"""

from sdi.graph.builder import build_dependency_graph
from sdi.graph.metrics import compute_graph_metrics

__all__ = [
    "build_dependency_graph",
    "compute_graph_metrics",
]
