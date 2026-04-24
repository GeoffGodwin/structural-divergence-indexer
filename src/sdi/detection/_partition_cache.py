"""Partition cache I/O and stability threshold debounce for Leiden detection.

Handles reading/writing the .sdi/cache/partition.json file atomically,
building warm-start initial_membership lists, applying the stability
threshold debounce filter, and computing stability scores.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import igraph

logger = logging.getLogger(__name__)

PARTITION_CACHE_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------


def _read_cache(cache_dir: Path) -> dict | None:
    """Read partition cache from disk.

    Args:
        cache_dir: Directory containing partition.json.

    Returns:
        Parsed cache dict, or None if the file is missing or corrupt.
    """
    cache_path = cache_dir / "partition.json"
    if not cache_path.exists():
        return None
    try:
        with open(cache_path) as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("cache_version"), str):
            return None
        return data
    except (json.JSONDecodeError, OSError, KeyError):
        logger.warning(
            "Partition cache at %s is corrupt; using cold start.", cache_path
        )
        return None


def _write_cache(cache_dir: Path, data: dict) -> None:
    """Atomically write partition cache to disk.

    Args:
        cache_dir: Target directory (created if absent).
        data: Cache dict to serialize as JSON.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "partition.json"
    tmp_fd, tmp_name = tempfile.mkstemp(dir=cache_dir, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp_name, cache_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Warm-start membership construction
# ---------------------------------------------------------------------------


def _build_initial_membership(graph: igraph.Graph, cache: dict) -> list[int]:
    """Map cached stable partition onto current graph vertices.

    New vertices not present in the cache are assigned to cluster 0.

    Args:
        graph: Current igraph graph with vertex attribute "name".
        cache: Previously written partition cache dict.

    Returns:
        List of initial cluster assignments, one per current vertex.
    """
    name_to_cluster: dict[str, int] = dict(
        zip(cache["vertex_names"], cache["stable_partition"])
    )
    names: list[str] = (
        graph.vs["name"] if "name" in graph.vertex_attributes() else []
    )
    return [name_to_cluster.get(name, 0) for name in names]


# ---------------------------------------------------------------------------
# Stability threshold debounce
# ---------------------------------------------------------------------------


def _apply_debounce(
    vertex_names: list[str],
    raw_partition: list[int],
    prev_cache: dict | None,
    threshold: int,
) -> tuple[list[int], dict]:
    """Apply stability threshold debounce to produce a stable partition.

    A node's stable cluster is updated only after it appears in the same new
    cluster for `threshold` consecutive runs.

    Args:
        vertex_names: Ordered vertex names for this run.
        raw_partition: Raw Leiden cluster assignments for each vertex.
        prev_cache: Previous partition cache (None on cold start).
        threshold: Consecutive runs required before a change is accepted.

    Returns:
        Tuple of (stable_partition, node_history). node_history is ready
        to be stored in the next cache write.
    """
    prev_history: dict = (
        prev_cache.get("node_history", {}) if prev_cache is not None else {}
    )
    stable_partition: list[int] = []
    node_history: dict = {}

    for name, raw_cluster in zip(vertex_names, raw_partition):
        entry = prev_history.get(name)
        if entry is None:
            stable_partition.append(raw_cluster)
            node_history[name] = {
                "stable_cluster": raw_cluster,
                "candidate_cluster": raw_cluster,
                "consecutive_runs": 0,
            }
            continue

        stable = entry["stable_cluster"]
        candidate = entry["candidate_cluster"]
        consec = entry["consecutive_runs"]

        if raw_cluster == stable:
            candidate = stable
            consec = 0
        elif raw_cluster == candidate:
            consec += 1
            if consec >= threshold:
                stable = raw_cluster
                consec = 0
        else:
            candidate = raw_cluster
            consec = 1

        stable_partition.append(stable)
        node_history[name] = {
            "stable_cluster": stable,
            "candidate_cluster": candidate,
            "consecutive_runs": consec,
        }

    return stable_partition, node_history


# ---------------------------------------------------------------------------
# Stability score
# ---------------------------------------------------------------------------


def _compute_stability_score(
    prev_cache: dict | None,
    new_stable: list[int],
    vertex_names: list[str],
) -> float:
    """Compute fraction of nodes retaining stable cluster membership.

    Compares the current stable partition against the previous stable partition.
    Returns 1.0 on cold start (no prior data to compare against).

    Args:
        prev_cache: Previous partition cache. None on cold start.
        new_stable: Current stable partition (after debounce).
        vertex_names: Vertex names corresponding to new_stable indices.

    Returns:
        Float in [0.0, 1.0].
    """
    if prev_cache is None:
        return 1.0
    prev_mapping: dict[str, int] = dict(
        zip(prev_cache["vertex_names"], prev_cache["stable_partition"])
    )
    matching = 0
    compared = 0
    for name, cluster in zip(vertex_names, new_stable):
        if name in prev_mapping:
            compared += 1
            if prev_mapping[name] == cluster:
                matching += 1
    return matching / compared if compared > 0 else 1.0
