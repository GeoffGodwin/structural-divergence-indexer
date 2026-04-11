"""Unit tests for Leiden community detection: detect_communities() behaviour.

Tests cover detection-level behaviour:
  - Cold-start determinism (same graph + seed → same partition)
  - Warm-start stability (unchanged graph → stability score 1.0)
  - Warm-start with graph change → high stability score
  - Gamma resolution parameter effect on cluster count
  - Trivial partition for small/empty graphs (< 10 nodes)
  - Partition cache written after each run
  - Missing or corrupt cache triggers cold start gracefully
  - CommunityResult shape and invariants

Internal function tests (debounce, cache I/O, metrics) are in
test_leiden_internals.py.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import igraph
import pytest

from sdi.config import SDIConfig
from sdi.detection import CommunityResult, detect_communities
from sdi.detection._partition_cache import (
    PARTITION_CACHE_VERSION,
    _read_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(n: int, edges: list[tuple[int, int]]) -> igraph.Graph:
    """Build a directed igraph with numbered vertex names."""
    g = igraph.Graph(n=n, directed=True)
    g.add_edges(edges)
    g.vs["name"] = [f"file{i}.py" for i in range(n)]
    return g


def _cluster_graph() -> igraph.Graph:
    """Three clear communities of 4 nodes each, weakly connected between them."""
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (8, 9), (9, 10), (10, 11), (11, 8),
        (3, 4), (7, 8),
    ]
    return _make_graph(12, edges)


def _default_config(**overrides) -> SDIConfig:
    """Return an SDIConfig with optional boundary overrides."""
    cfg = SDIConfig()
    cfg.core.random_seed = 42
    cfg.boundaries.leiden_gamma = 1.0
    cfg.boundaries.stability_threshold = 3
    for key, value in overrides.items():
        setattr(cfg.boundaries, key, value)
    return cfg


# ---------------------------------------------------------------------------
# Cold-start determinism
# ---------------------------------------------------------------------------


def test_cold_start_determinism(tmp_path: Path) -> None:
    """Same graph + same seed → identical partition across independent runs."""
    graph = _cluster_graph()
    cfg = _default_config()

    result1 = detect_communities(graph, cfg, tmp_path / "cache1")
    result2 = detect_communities(graph, cfg, tmp_path / "cache2")

    assert result1.partition == result2.partition
    assert result1.cluster_count == result2.cluster_count


# ---------------------------------------------------------------------------
# Warm-start stability
# ---------------------------------------------------------------------------


def test_warm_start_unchanged_graph_stability_one(tmp_path: Path) -> None:
    """Warm start on an unchanged graph produces stability_score == 1.0."""
    graph = _cluster_graph()
    cfg = _default_config()
    cache_dir = tmp_path / "cache"

    detect_communities(graph, cfg, cache_dir)
    result = detect_communities(graph, cfg, cache_dir)

    assert result.stability_score == 1.0


def test_warm_start_small_change_high_stability(tmp_path: Path) -> None:
    """Adding one edge to a stable graph gives stability > 0.9."""
    graph = _cluster_graph()
    cfg = _default_config()
    cache_dir = tmp_path / "cache"

    detect_communities(graph, cfg, cache_dir)
    graph.add_edge(0, 2)
    result = detect_communities(graph, cfg, cache_dir)

    assert result.stability_score > 0.9


# ---------------------------------------------------------------------------
# Gamma (resolution parameter) effect
# ---------------------------------------------------------------------------


def test_higher_gamma_produces_more_clusters(tmp_path: Path) -> None:
    """Higher leiden_gamma resolution generally yields more, smaller clusters."""
    edges = [(i, i + 1) for i in range(19)] + [(0, 5), (5, 10), (10, 15), (15, 19)]
    graph = _make_graph(20, edges)

    result_low = detect_communities(graph, _default_config(leiden_gamma=0.5), tmp_path / "low")
    result_high = detect_communities(graph, _default_config(leiden_gamma=5.0), tmp_path / "high")

    assert result_high.cluster_count >= result_low.cluster_count


# ---------------------------------------------------------------------------
# Small / empty graphs: trivial partition
# ---------------------------------------------------------------------------


def test_small_graph_returns_trivial_partition(tmp_path: Path) -> None:
    """Graph with fewer than 10 nodes returns trivial partition (all cluster 0)."""
    graph = _make_graph(5, [(0, 1), (1, 2), (2, 3)])
    cfg = _default_config()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = detect_communities(graph, cfg, tmp_path / "cache")

    assert all(c == 0 for c in result.partition)
    assert result.cluster_count == 1
    assert result.stability_score == 1.0
    assert any("insufficient structure" in str(w.message) for w in caught)


def test_empty_graph_returns_trivial_partition(tmp_path: Path) -> None:
    """Empty graph (0 nodes) returns trivial partition without error."""
    graph = igraph.Graph(n=0, directed=True)
    cfg = _default_config()

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = detect_communities(graph, cfg, tmp_path / "cache")

    assert result.partition == []
    assert result.cluster_count == 0
    assert result.stability_score == 1.0


# ---------------------------------------------------------------------------
# Cache written after each run
# ---------------------------------------------------------------------------


def test_cache_is_written_after_run(tmp_path: Path) -> None:
    """detect_communities writes partition.json to cache_dir."""
    graph = _cluster_graph()
    cache_dir = tmp_path / "cache"

    assert not (cache_dir / "partition.json").exists()
    detect_communities(graph, _default_config(), cache_dir)
    assert (cache_dir / "partition.json").exists()

    cache = _read_cache(cache_dir)
    assert cache is not None
    assert cache["cache_version"] == PARTITION_CACHE_VERSION
    assert len(cache["vertex_names"]) == graph.vcount()


# ---------------------------------------------------------------------------
# Missing / corrupt cache → cold start
# ---------------------------------------------------------------------------


def test_missing_cache_triggers_cold_start(tmp_path: Path) -> None:
    """Missing cache file causes cold start without error."""
    result = detect_communities(
        _cluster_graph(), _default_config(), tmp_path / "no_cache_here"
    )
    assert result.stability_score == 1.0
    assert result.cluster_count > 0


def test_corrupt_cache_falls_back_to_cold_start(tmp_path: Path) -> None:
    """Corrupt cache JSON causes cold start gracefully."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "partition.json").write_text("{ not valid json }")

    result = detect_communities(_cluster_graph(), _default_config(), cache_dir)
    assert result.cluster_count > 0


# ---------------------------------------------------------------------------
# CommunityResult invariants
# ---------------------------------------------------------------------------


def test_community_result_fields(tmp_path: Path) -> None:
    """CommunityResult has all required fields with correct types."""
    graph = _cluster_graph()
    result = detect_communities(graph, _default_config(), tmp_path / "cache")

    assert isinstance(result.partition, list)
    assert len(result.partition) == graph.vcount()
    assert isinstance(result.stability_score, float)
    assert 0.0 <= result.stability_score <= 1.0
    assert isinstance(result.cluster_count, int)
    assert result.cluster_count > 0
    assert isinstance(result.inter_cluster_edges, list)
    assert isinstance(result.surface_area_ratios, dict)
    assert isinstance(result.vertex_names, list)
    assert len(result.vertex_names) == graph.vcount()


def test_community_result_vertex_names_ordered(tmp_path: Path) -> None:
    """vertex_names in result corresponds to graph vertex order."""
    graph = _cluster_graph()
    result = detect_communities(graph, _default_config(), tmp_path / "cache")

    assert result.vertex_names == graph.vs["name"]
