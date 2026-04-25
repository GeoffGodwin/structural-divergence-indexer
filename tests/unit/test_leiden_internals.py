"""Unit tests for Leiden internal helpers: debounce, cache I/O, and metrics.

Tests cover:
  - Stability threshold debounce (node must appear N consecutive runs)
  - Flicker resets debounce counter
  - Partition cache round-trip (write then read)
  - Inter-cluster edge counting
  - Surface area ratio computation
"""

from __future__ import annotations

from pathlib import Path

import igraph
import pytest

from sdi.detection._partition_cache import (
    PARTITION_CACHE_VERSION,
    _apply_debounce,
    _build_initial_membership,
    _compute_stability_score,
    _read_cache,
    _write_cache,
)
from sdi.detection.leiden import (
    _compute_inter_cluster_edges,
    _compute_surface_area_ratios,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph(n: int, edges: list[tuple[int, int]]) -> igraph.Graph:
    g = igraph.Graph(n=n, directed=True)
    g.add_edges(edges)
    g.vs["name"] = [f"file{i}.py" for i in range(n)]
    return g


def _prev_cache(names: list[str], partition: list[int]) -> dict:
    """Build a minimal prev_cache dict for debounce tests."""
    return {
        "cache_version": PARTITION_CACHE_VERSION,
        "vertex_names": names,
        "stable_partition": partition,
        "node_history": {
            n: {"stable_cluster": c, "candidate_cluster": c, "consecutive_runs": 0} for n, c in zip(names, partition)
        },
    }


# ---------------------------------------------------------------------------
# Stability threshold debounce
# ---------------------------------------------------------------------------


def test_debounce_requires_n_consecutive_runs() -> None:
    """A node that changes clusters isn't promoted until N consecutive runs."""
    names = ["a.py", "b.py", "c.py"]
    threshold = 3

    cache = _prev_cache(names, [0, 0, 1])

    # Run 1: b.py moves to cluster 1 — 1 consecutive run (not yet promoted)
    stable1, hist1 = _apply_debounce(names, [0, 1, 1], cache, threshold)
    assert stable1[1] == 0, "b.py unchanged after run 1"
    assert hist1["b.py"]["consecutive_runs"] == 1

    # Run 2: b.py still in cluster 1 — 2 consecutive runs (not yet promoted)
    cache2 = {**cache, "node_history": hist1}
    stable2, hist2 = _apply_debounce(names, [0, 1, 1], cache2, threshold)
    assert stable2[1] == 0, "b.py unchanged after run 2"
    assert hist2["b.py"]["consecutive_runs"] == 2

    # Run 3: b.py still in cluster 1 — 3 consecutive runs → promoted
    cache3 = {**cache, "node_history": hist2}
    stable3, hist3 = _apply_debounce(names, [0, 1, 1], cache3, threshold)
    assert stable3[1] == 1, "b.py promoted after 3 consecutive runs"
    assert hist3["b.py"]["consecutive_runs"] == 0


def test_debounce_flicker_resets_counter() -> None:
    """A node that flickers back to stable cluster resets the debounce counter."""
    names = ["x.py"]
    threshold = 3

    cache = {
        "cache_version": PARTITION_CACHE_VERSION,
        "vertex_names": names,
        "stable_partition": [0],
        "node_history": {
            "x.py": {
                "stable_cluster": 0,
                "candidate_cluster": 1,
                "consecutive_runs": 2,  # one run away from promotion
            }
        },
    }

    stable, history = _apply_debounce(names, [0], cache, threshold)
    assert stable[0] == 0, "stable cluster unchanged after flicker"
    assert history["x.py"]["consecutive_runs"] == 0
    assert history["x.py"]["candidate_cluster"] == 0


def test_debounce_new_node_accepted_immediately() -> None:
    """A node with no prior history is accepted into its raw cluster immediately."""
    names = ["old.py", "new.py"]
    cache = _prev_cache(["old.py"], [0])

    stable, history = _apply_debounce(names, [0, 2], cache, threshold=3)
    assert stable[1] == 2, "new node accepted immediately"
    assert history["new.py"]["stable_cluster"] == 2
    assert history["new.py"]["consecutive_runs"] == 0


def test_debounce_cold_start_accepts_raw_partition() -> None:
    """Cold start (no prev_cache) sets stable partition equal to raw partition."""
    names = ["a.py", "b.py"]
    stable, history = _apply_debounce(names, [0, 1], None, threshold=3)
    assert stable == [0, 1]
    assert history["a.py"]["stable_cluster"] == 0
    assert history["b.py"]["stable_cluster"] == 1


def test_debounce_different_candidate_resets_counter() -> None:
    """Switching to a new candidate (not stable or tracked) resets counter to 1."""
    names = ["z.py"]
    cache = {
        "cache_version": PARTITION_CACHE_VERSION,
        "vertex_names": names,
        "stable_partition": [0],
        "node_history": {
            "z.py": {
                "stable_cluster": 0,
                "candidate_cluster": 1,
                "consecutive_runs": 2,
            }
        },
    }

    # Node moves to cluster 2 (different from both stable=0 and candidate=1)
    stable, history = _apply_debounce(names, [2], cache, threshold=3)
    assert stable[0] == 0, "stable unchanged"
    assert history["z.py"]["candidate_cluster"] == 2
    assert history["z.py"]["consecutive_runs"] == 1


# ---------------------------------------------------------------------------
# Stability score
# ---------------------------------------------------------------------------


def test_stability_score_cold_start_is_one() -> None:
    """Cold start (no prev_cache) returns stability_score 1.0."""
    score = _compute_stability_score(None, [0, 1], ["a.py", "b.py"])
    assert score == 1.0


def test_stability_score_all_unchanged() -> None:
    """All nodes unchanged gives stability_score 1.0."""
    cache = _prev_cache(["a.py", "b.py"], [0, 1])
    score = _compute_stability_score(cache, [0, 1], ["a.py", "b.py"])
    assert score == 1.0


def test_stability_score_half_changed() -> None:
    """Half of nodes changed gives stability_score 0.5."""
    cache = _prev_cache(["a.py", "b.py"], [0, 1])
    score = _compute_stability_score(cache, [0, 0], ["a.py", "b.py"])
    assert score == pytest.approx(0.5)


def test_stability_score_new_node_not_counted() -> None:
    """New nodes (not in prev_cache) are excluded from stability score."""
    cache = _prev_cache(["a.py"], [0])
    # a.py unchanged, new.py has no history
    score = _compute_stability_score(cache, [0, 1], ["a.py", "new.py"])
    assert score == 1.0


# ---------------------------------------------------------------------------
# Partition cache round-trip
# ---------------------------------------------------------------------------


def test_cache_round_trip(tmp_path: Path) -> None:
    """Writing then reading the cache produces identical data."""
    cache_dir = tmp_path / "cache"
    data = {
        "cache_version": PARTITION_CACHE_VERSION,
        "vertex_names": ["a.py", "b.py"],
        "stable_partition": [0, 1],
        "node_history": {
            "a.py": {"stable_cluster": 0, "candidate_cluster": 0, "consecutive_runs": 0},
            "b.py": {"stable_cluster": 1, "candidate_cluster": 1, "consecutive_runs": 0},
        },
    }
    _write_cache(cache_dir, data)
    loaded = _read_cache(cache_dir)

    assert loaded is not None
    assert loaded["cache_version"] == PARTITION_CACHE_VERSION
    assert loaded["vertex_names"] == data["vertex_names"]
    assert loaded["stable_partition"] == data["stable_partition"]
    assert loaded["node_history"] == data["node_history"]


def test_read_cache_missing_returns_none(tmp_path: Path) -> None:
    """_read_cache returns None when the cache file does not exist."""
    assert _read_cache(tmp_path / "nonexistent") is None


def test_read_cache_corrupt_returns_none(tmp_path: Path) -> None:
    """_read_cache returns None for corrupt JSON."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "partition.json").write_text("{ definitely not json")
    assert _read_cache(cache_dir) is None


def test_write_cache_creates_directory(tmp_path: Path) -> None:
    """_write_cache creates the cache directory if it does not exist."""
    cache_dir = tmp_path / "deep" / "nested" / "cache"
    _write_cache(cache_dir, {"cache_version": "0.1.0", "data": []})
    assert (cache_dir / "partition.json").exists()


def test_read_cache_toplevel_array_returns_none(tmp_path: Path) -> None:
    """_read_cache returns None when file contains a JSON array (not a dict).

    A top-level JSON array parses without JSONDecodeError but calling .get()
    on a list raises AttributeError. The stated contract is that any corrupt or
    unrecognised cache content should produce a cold start (return None), not
    an unhandled exception.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "partition.json").write_text("[1, 2, 3]")
    result = _read_cache(cache_dir)
    assert result is None, "_read_cache should return None for a top-level JSON array, not raise AttributeError"


# ---------------------------------------------------------------------------
# _build_initial_membership — missing-key coverage
# ---------------------------------------------------------------------------


def test_build_initial_membership_missing_vertex_names_raises() -> None:
    """Cache that passes _read_cache validation but lacks 'vertex_names' raises KeyError.

    _read_cache only validates that cache_version is a string; it does not
    check for vertex_names or stable_partition. If those keys are absent,
    _build_initial_membership will raise KeyError, which propagates to the
    caller (run_leiden). This test documents the current behaviour so any
    future silent-failure fix is detectable via a test update.
    """
    g = igraph.Graph(n=2, directed=True)
    g.vs["name"] = ["a.py", "b.py"]

    cache_missing_vertex_names = {
        "cache_version": PARTITION_CACHE_VERSION,
        # vertex_names intentionally absent
        "stable_partition": [0, 1],
        "node_history": {},
    }
    with pytest.raises(KeyError):
        _build_initial_membership(g, cache_missing_vertex_names)


def test_build_initial_membership_missing_stable_partition_raises() -> None:
    """Cache lacking 'stable_partition' raises KeyError in _build_initial_membership.

    Same rationale as the vertex_names test above: _read_cache does not guard
    against missing stable_partition, so _build_initial_membership will raise.
    This documents the propagation behaviour.
    """
    g = igraph.Graph(n=2, directed=True)
    g.vs["name"] = ["a.py", "b.py"]

    cache_missing_stable_partition = {
        "cache_version": PARTITION_CACHE_VERSION,
        "vertex_names": ["a.py", "b.py"],
        # stable_partition intentionally absent
        "node_history": {},
    }
    with pytest.raises(KeyError):
        _build_initial_membership(g, cache_missing_stable_partition)


# ---------------------------------------------------------------------------
# Inter-cluster edge counting
# ---------------------------------------------------------------------------


def test_inter_cluster_edges_no_cross_edges() -> None:
    """Disconnected graph has no inter-cluster edges."""
    g = _make_graph(4, [])
    assert _compute_inter_cluster_edges(g, [0, 0, 1, 1]) == []


def test_inter_cluster_edges_counts_correctly() -> None:
    """Cross-cluster edges are counted by (source_cluster, target_cluster)."""
    g = _make_graph(4, [(0, 2), (1, 3), (2, 1)])
    partition = [0, 0, 1, 1]
    edges = _compute_inter_cluster_edges(g, partition)
    assert {"source_cluster": 0, "target_cluster": 1, "count": 2} in edges
    assert {"source_cluster": 1, "target_cluster": 0, "count": 1} in edges


def test_inter_cluster_edges_sorted() -> None:
    """Result is sorted by (source_cluster, target_cluster)."""
    g = _make_graph(4, [(2, 0), (0, 2)])
    partition = [0, 0, 1, 1]
    edges = _compute_inter_cluster_edges(g, partition)
    keys = [(e["source_cluster"], e["target_cluster"]) for e in edges]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Surface area ratio computation
# ---------------------------------------------------------------------------


def test_surface_area_ratios_all_internal() -> None:
    """Clusters with only internal edges have surface_area_ratio 0.0."""
    g = _make_graph(4, [(0, 1), (2, 3)])
    ratios = _compute_surface_area_ratios(g, [0, 0, 1, 1])
    assert ratios[0] == 0.0
    assert ratios[1] == 0.0


def test_surface_area_ratios_boundary_edges() -> None:
    """Cluster with one external and one internal edge has ratio 0.5."""
    # Cluster 0: nodes 0,1 — edges (0→1) internal, (1→2) external
    # Cluster 1: nodes 2,3 — edge (2→3) internal
    g = _make_graph(4, [(0, 1), (1, 2), (2, 3)])
    ratios = _compute_surface_area_ratios(g, [0, 0, 1, 1])
    assert ratios[0] == pytest.approx(0.5)


def test_surface_area_ratios_empty_cluster() -> None:
    """Cluster with no edges has surface_area_ratio 0.0."""
    g = _make_graph(3, [(0, 1)])
    # partition [0, 0, 2]: cluster 2 (node 2) has no edges; actual IDs are {0, 2}
    ratios = _compute_surface_area_ratios(g, [0, 0, 2])
    assert set(ratios.keys()) == {0, 2}
    assert ratios[2] == 0.0


def test_surface_area_ratios_non_contiguous_ids() -> None:
    """Keys match actual cluster IDs in partition, not a range-based assumption.

    When the debounce is mid-transition, stable_partition can contain
    non-contiguous IDs (e.g., [0, 4] with no 1/2/3). The returned dict
    must have keys {0, 4}, not {0, 1}.
    """
    # Nodes 0,1 in cluster 0; nodes 2,3 in cluster 4 — clusters 1/2/3 absent
    g = _make_graph(4, [(0, 2)])
    partition = [0, 0, 4, 4]
    ratios = _compute_surface_area_ratios(g, partition)
    assert set(ratios.keys()) == {0, 4}
    # edge (0→2): sc=0, tc=4 — external for both; 1 external / 1 total each
    assert ratios[0] == pytest.approx(1.0)
    assert ratios[4] == pytest.approx(1.0)
