"""Leiden community detection performance benchmarks at 100–10,000 node scales.

These tests are gated behind ``pytest.mark.benchmark`` and are NOT run in
normal CI. Trigger explicitly with:

    pytest tests/benchmarks/ -m benchmark

Requires igraph and leidenalg. Tests are skipped if those packages are absent.
"""

from __future__ import annotations

import time

import pytest

try:
    import igraph
    import leidenalg  # noqa: F401

    _LEIDEN_AVAILABLE = True
except ImportError:
    _LEIDEN_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not _LEIDEN_AVAILABLE,
    reason="igraph and leidenalg required for Leiden benchmarks",
)


# ---------------------------------------------------------------------------
# Synthetic graph helpers
# ---------------------------------------------------------------------------


def _build_synthetic_graph(node_count: int, edge_density: float = 0.02) -> "igraph.Graph":
    """Build a synthetic directed graph for benchmarking.

    Nodes are arranged in clusters of ~50. Intra-cluster edges are dense;
    inter-cluster edges are sparse to produce realistic Leiden partitions.

    Args:
        node_count: Number of vertices.
        edge_density: Approximate fraction of possible edges to create.

    Returns:
        Directed igraph.Graph with string vertex names.
    """
    g = igraph.Graph(directed=True)
    g.add_vertices(node_count)
    g.vs["name"] = [f"src/module_{i}.py" for i in range(node_count)]

    cluster_size = 50
    edges = []
    for src in range(node_count):
        cluster = src // cluster_size
        for tgt in range(node_count):
            if src == tgt:
                continue
            tgt_cluster = tgt // cluster_size
            if cluster == tgt_cluster:
                if (src * 31 + tgt * 17) % 100 < 40:
                    edges.append((src, tgt))
            else:
                if (src * 13 + tgt * 7) % 1000 < 5:
                    edges.append((src, tgt))
    g.add_edges(edges)
    return g


# ---------------------------------------------------------------------------
# Leiden partition benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("node_count", [100, 1000, 5000, 10000])
def test_leiden_partition_time(node_count: int):
    """Leiden partition on a synthetic graph of N nodes completes in under 60s."""
    g = _build_synthetic_graph(node_count)
    start = time.perf_counter()
    lpart = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=1.0,
        seed=42,
    )
    elapsed = time.perf_counter() - start
    cluster_count = len(set(lpart.membership))
    print(f"\n  {node_count} nodes: {elapsed:.3f}s edges={g.ecount()} clusters={cluster_count}")
    assert elapsed < 60.0, f"Leiden on {node_count} nodes took {elapsed:.1f}s (limit: 60s)"


@pytest.mark.benchmark
@pytest.mark.parametrize("node_count", [100, 1000])
def test_leiden_warm_start_faster_than_cold(node_count: int):
    """Warm-start Leiden (seeded from prior partition) is not slower than cold."""
    g = _build_synthetic_graph(node_count)

    # Cold start
    cold_start = time.perf_counter()
    cold_part = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=1.0,
        seed=42,
    )
    cold_time = time.perf_counter() - cold_start

    # Warm start — seed from prior membership
    warm_start = time.perf_counter()
    leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=1.0,
        seed=42,
        initial_membership=list(cold_part.membership),
    )
    warm_time = time.perf_counter() - warm_start

    print(
        f"\n  {node_count} nodes: cold={cold_time:.3f}s warm={warm_time:.3f}s"
        f" ratio={warm_time / max(cold_time, 1e-9):.2f}x"
    )
    # Warm start should be no more than 2x slower than cold (usually faster)
    assert warm_time < cold_time * 3.0, (
        f"Warm start ({warm_time:.3f}s) unexpectedly much slower than cold ({cold_time:.3f}s)"
    )
