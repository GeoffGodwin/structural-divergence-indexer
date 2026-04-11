"""Unit tests for sdi.graph.metrics — graph metric computation."""

from __future__ import annotations

import igraph
import pytest

from sdi.graph.metrics import compute_graph_metrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph(
    n: int, edges: list[tuple[int, int]], names: list[str] | None = None
) -> igraph.Graph:
    """Build a directed igraph with optional vertex names."""
    g = igraph.Graph(n=n, directed=True)
    g.add_edges(edges)
    if names:
        g.vs["name"] = names
    return g


# ---------------------------------------------------------------------------
# Empty graph
# ---------------------------------------------------------------------------

class TestEmptyGraph:
    def test_node_count_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["node_count"] == 0

    def test_edge_count_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["edge_count"] == 0

    def test_density_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["density"] == 0.0

    def test_cycle_count_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["cycle_count"] == 0

    def test_component_count_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["component_count"] == 0

    def test_hub_concentration_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["hub_concentration"] == 0.0

    def test_hub_nodes_empty(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["hub_nodes"] == []

    def test_max_depth_zero(self) -> None:
        g = igraph.Graph(directed=True)
        m = compute_graph_metrics(g)
        assert m["max_depth"] == 0


# ---------------------------------------------------------------------------
# Single node
# ---------------------------------------------------------------------------

class TestSingleNode:
    def test_single_node_no_edges(self) -> None:
        g = igraph.Graph(n=1, directed=True)
        m = compute_graph_metrics(g)
        assert m["node_count"] == 1
        assert m["edge_count"] == 0
        assert m["density"] == 0.0
        assert m["cycle_count"] == 0
        assert m["component_count"] == 1
        assert m["hub_concentration"] == 0.0
        assert m["max_depth"] == 0


# ---------------------------------------------------------------------------
# Density
# ---------------------------------------------------------------------------

class TestDensity:
    def test_density_complete_graph(self) -> None:
        # 3 nodes fully connected (directed): 3*2=6 possible edges, 6 actual
        g = _make_graph(3, [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)])
        m = compute_graph_metrics(g)
        assert m["density"] == pytest.approx(1.0)

    def test_density_half_connected(self) -> None:
        # 4 nodes, 4 edges out of 12 possible = density ~0.333
        g = _make_graph(4, [(0, 1), (0, 2), (1, 3), (2, 3)])
        m = compute_graph_metrics(g)
        assert 0.0 < m["density"] < 1.0

    def test_density_two_nodes_one_edge(self) -> None:
        # 2 nodes, 1 directed edge: density = 1/2 = 0.5
        g = _make_graph(2, [(0, 1)])
        m = compute_graph_metrics(g)
        assert m["density"] == pytest.approx(0.5)

    def test_density_no_edges(self) -> None:
        g = _make_graph(5, [])
        m = compute_graph_metrics(g)
        assert m["density"] == 0.0


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

class TestCycleCount:
    def test_acyclic_graph_zero_cycles(self) -> None:
        # Linear chain: 0→1→2→3
        g = _make_graph(4, [(0, 1), (1, 2), (2, 3)])
        m = compute_graph_metrics(g)
        assert m["cycle_count"] == 0

    def test_dag_with_diamond_zero_cycles(self) -> None:
        # 0→1, 0→2, 1→3, 2→3 (no cycle)
        g = _make_graph(4, [(0, 1), (0, 2), (1, 3), (2, 3)])
        m = compute_graph_metrics(g)
        assert m["cycle_count"] == 0

    def test_simple_cycle_one_cycle(self) -> None:
        # 0→1→2→0
        g = _make_graph(3, [(0, 1), (1, 2), (2, 0)])
        m = compute_graph_metrics(g)
        assert m["cycle_count"] == 1

    def test_two_disjoint_cycles(self) -> None:
        # Cycle 1: 0→1→0; Cycle 2: 2→3→2
        g = _make_graph(4, [(0, 1), (1, 0), (2, 3), (3, 2)])
        m = compute_graph_metrics(g)
        assert m["cycle_count"] == 2

    def test_mutual_import_is_cycle(self) -> None:
        # a→b, b→a = one 2-node cycle
        g = _make_graph(2, [(0, 1), (1, 0)])
        m = compute_graph_metrics(g)
        assert m["cycle_count"] >= 1


# ---------------------------------------------------------------------------
# Connected components
# ---------------------------------------------------------------------------

class TestComponentCount:
    def test_fully_connected(self) -> None:
        g = _make_graph(3, [(0, 1), (1, 2)])
        m = compute_graph_metrics(g)
        assert m["component_count"] == 1

    def test_two_disconnected_components(self) -> None:
        # 0→1 and 2→3 are disconnected
        g = _make_graph(4, [(0, 1), (2, 3)])
        m = compute_graph_metrics(g)
        assert m["component_count"] == 2

    def test_three_isolated_nodes(self) -> None:
        g = igraph.Graph(n=3, directed=True)
        m = compute_graph_metrics(g)
        assert m["component_count"] == 3


# ---------------------------------------------------------------------------
# Max depth
# ---------------------------------------------------------------------------

class TestMaxDepth:
    def test_linear_chain_depth(self) -> None:
        # 0→1→2→3→4: 4 hops from node 0 to node 4
        g = _make_graph(5, [(0, 1), (1, 2), (2, 3), (3, 4)])
        m = compute_graph_metrics(g)
        assert m["max_depth"] == 4

    def test_diamond_dag_depth(self) -> None:
        # 0→1, 0→2, 1→3, 2→3: longest path = 2 hops
        g = _make_graph(4, [(0, 1), (0, 2), (1, 3), (2, 3)])
        m = compute_graph_metrics(g)
        assert m["max_depth"] == 2

    def test_single_edge_depth_one(self) -> None:
        g = _make_graph(2, [(0, 1)])
        m = compute_graph_metrics(g)
        assert m["max_depth"] == 1

    def test_no_edges_depth_zero(self) -> None:
        g = igraph.Graph(n=4, directed=True)
        m = compute_graph_metrics(g)
        assert m["max_depth"] == 0


# ---------------------------------------------------------------------------
# Hub concentration
# ---------------------------------------------------------------------------

class TestHubConcentration:
    def test_fewer_than_three_nodes_is_zero(self) -> None:
        g = _make_graph(2, [(0, 1)])
        m = compute_graph_metrics(g)
        assert m["hub_concentration"] == 0.0
        assert m["hub_nodes"] == []

    def test_no_hubs_below_threshold(self) -> None:
        # 4 nodes; max in-degree = 2 (below threshold of 3)
        g = _make_graph(4, [(0, 2), (1, 2), (0, 3), (1, 3)])
        m = compute_graph_metrics(g)
        assert m["hub_concentration"] == 0.0
        assert m["hub_nodes"] == []

    def test_hub_detected_at_threshold(self) -> None:
        # Node 0 has in-degree 4 (above threshold of 3)
        g = _make_graph(
            5,
            [(1, 0), (2, 0), (3, 0), (4, 0)],
            names=["a.py", "b.py", "c.py", "d.py", "e.py"],
        )
        m = compute_graph_metrics(g)
        # Node 0 ("a.py") has in-degree 4 ≥ 3
        assert "a.py" in m["hub_nodes"]
        assert m["hub_concentration"] > 0.0

    def test_hub_concentration_is_float(self) -> None:
        g = _make_graph(4, [(0, 2), (1, 2)])
        m = compute_graph_metrics(g)
        assert isinstance(m["hub_concentration"], float)

    def test_hub_concentration_in_range(self) -> None:
        # 5 nodes, two hubs with in-degree >= 3
        g = _make_graph(
            5,
            [(1, 0), (2, 0), (3, 0), (1, 4), (2, 4), (3, 4)],
            names=["a.py", "b.py", "c.py", "d.py", "e.py"],
        )
        m = compute_graph_metrics(g)
        assert 0.0 <= m["hub_concentration"] <= 1.0

    def test_hub_nodes_uses_vertex_names(self) -> None:
        g = _make_graph(
            4,
            [(0, 3), (1, 3), (2, 3)],
            names=["x.py", "y.py", "z.py", "hub.py"],
        )
        m = compute_graph_metrics(g)
        assert "hub.py" in m["hub_nodes"]

    def test_hub_nodes_unnamed_graph_uses_indices(self) -> None:
        g = _make_graph(4, [(0, 3), (1, 3), (2, 3)])
        m = compute_graph_metrics(g)
        assert "3" in m["hub_nodes"]


# ---------------------------------------------------------------------------
# Return type and schema key presence
# ---------------------------------------------------------------------------

class TestReturnSchema:
    REQUIRED_KEYS = {
        "node_count",
        "edge_count",
        "density",
        "cycle_count",
        "hub_concentration",
        "hub_nodes",
        "component_count",
        "max_depth",
    }

    def test_all_keys_present(self) -> None:
        g = _make_graph(3, [(0, 1), (1, 2)])
        m = compute_graph_metrics(g)
        assert self.REQUIRED_KEYS.issubset(m.keys())

    def test_type_node_count_int(self) -> None:
        g = _make_graph(3, [(0, 1)])
        assert isinstance(compute_graph_metrics(g)["node_count"], int)

    def test_type_density_float(self) -> None:
        g = _make_graph(3, [(0, 1)])
        assert isinstance(compute_graph_metrics(g)["density"], float)

    def test_type_cycle_count_int(self) -> None:
        g = _make_graph(3, [(0, 1)])
        assert isinstance(compute_graph_metrics(g)["cycle_count"], int)

    def test_type_hub_nodes_list(self) -> None:
        g = _make_graph(3, [(0, 1)])
        assert isinstance(compute_graph_metrics(g)["hub_nodes"], list)
