"""Private helpers for intent divergence computation.

Not part of the public API — called only by boundaries.compute_intent_divergence().
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sdi.detection.boundaries import BoundarySpec, ModuleSpec


def _file_to_module(file_path: str, modules: list[ModuleSpec]) -> str | None:
    """Return the module name whose paths include file_path, or None."""
    for module in modules:
        for prefix in module.paths:
            if file_path.startswith(prefix):
                return module.name
    return None


def _build_cluster_module_map(
    partition_data: dict[str, Any],
    modules: list[ModuleSpec],
) -> dict[int, str | None]:
    """Map each cluster ID to its primary module (plurality of matching files).

    Args:
        partition_data: Partition dict from snapshot storage.
        modules: Module specs from BoundarySpec.

    Returns:
        Dict mapping cluster_id to module name, or None if unclassified.
    """
    vertex_names: list[str] = partition_data.get("vertex_names", [])
    partition: list[int] = partition_data.get("partition", [])
    if not vertex_names or not partition:
        return {}

    cluster_counts: dict[int, dict[str, int]] = {}
    for file_path, cid in zip(vertex_names, partition):
        mod = _file_to_module(file_path, modules)
        if mod:
            cluster_counts.setdefault(cid, {})
            cluster_counts[cid][mod] = cluster_counts[cid].get(mod, 0) + 1

    result: dict[int, str | None] = {}
    for cid in set(partition):
        counts = cluster_counts.get(cid)
        result[cid] = max(counts, key=lambda m: counts[m]) if counts else None
    return result


def _find_misplaced_files(
    spec: BoundarySpec,
    partition_data: dict[str, Any],
) -> list[str]:
    """Return file paths whose detected cluster differs from their module's home cluster.

    A module's home cluster is the cluster containing the plurality of that
    module's files. A file is misplaced if it belongs to a module by path but
    lands in a different cluster.

    Args:
        spec: Ratified boundary specification.
        partition_data: Partition dict from snapshot storage.

    Returns:
        List of misplaced file paths.
    """
    vertex_names: list[str] = partition_data.get("vertex_names", [])
    partition: list[int] = partition_data.get("partition", [])
    if not vertex_names or not partition:
        return []

    module_cluster_counts: dict[str, dict[int, int]] = {}
    for file_path, cid in zip(vertex_names, partition):
        mod = _file_to_module(file_path, spec.modules)
        if mod:
            module_cluster_counts.setdefault(mod, {})
            module_cluster_counts[mod][cid] = module_cluster_counts[mod].get(cid, 0) + 1

    module_home: dict[str, int] = {
        mod: max(counts, key=lambda c: counts[c])
        for mod, counts in module_cluster_counts.items()
    }

    return [
        file_path
        for file_path, cid in zip(vertex_names, partition)
        if (mod := _file_to_module(file_path, spec.modules))
        and module_home.get(mod) is not None
        and cid != module_home[mod]
    ]


def _find_unauthorized_cross_boundary(
    spec: BoundarySpec,
    partition_data: dict[str, Any],
    cluster_module: dict[int, str | None],
) -> list[dict[str, Any]]:
    """Return inter-cluster edges whose module pairing is not in allowed_cross_domain.

    Args:
        spec: Ratified boundary specification.
        partition_data: Partition dict from snapshot storage.
        cluster_module: Map of cluster_id to primary module name.

    Returns:
        List of violation dicts with from_module, to_module, count.
    """
    inter_cluster_edges: list[dict] = partition_data.get("inter_cluster_edges", [])
    if not inter_cluster_edges:
        return []

    allowed: set[tuple[str, str]] = {(a.from_module, a.to) for a in spec.allowed_cross_domain}

    violations: list[dict[str, Any]] = []
    for edge in inter_cluster_edges:
        src = cluster_module.get(edge["source_cluster"])
        tgt = cluster_module.get(edge["target_cluster"])
        if src and tgt and src != tgt and (src, tgt) not in allowed:
            violations.append(
                {"from_module": src, "to_module": tgt, "count": edge.get("count", 1)}
            )
    return violations


def _find_layer_violations(
    spec: BoundarySpec,
    partition_data: dict[str, Any],
    cluster_module: dict[int, str | None],
) -> list[dict[str, Any]]:
    """Return inter-cluster edges that violate the declared layer direction.

    For "downward" direction: a module in a higher layer (lower rank index) may
    depend on a lower layer (higher rank index), but not the reverse. A violation
    is when source_rank > target_rank (source is in a lower layer than target,
    meaning it flows upward against the declared direction).

    Args:
        spec: Ratified boundary specification.
        partition_data: Partition dict from snapshot storage.
        cluster_module: Map of cluster_id to primary module name.

    Returns:
        List of violation dicts with from_module, to_module, from_layer, to_layer, count.
    """
    if not spec.layers or spec.layers.direction != "downward":
        return []

    layer_rank = {layer: i for i, layer in enumerate(spec.layers.ordering)}
    module_layer = {m.name: m.layer for m in spec.modules if m.layer}
    inter_cluster_edges: list[dict] = partition_data.get("inter_cluster_edges", [])

    violations: list[dict[str, Any]] = []
    for edge in inter_cluster_edges:
        src_mod = cluster_module.get(edge["source_cluster"])
        tgt_mod = cluster_module.get(edge["target_cluster"])
        if not src_mod or not tgt_mod or src_mod == tgt_mod:
            continue
        src_layer = module_layer.get(src_mod)
        tgt_layer = module_layer.get(tgt_mod)
        if not src_layer or not tgt_layer:
            continue
        src_rank = layer_rank.get(src_layer, -1)
        tgt_rank = layer_rank.get(tgt_layer, -1)
        if src_rank < 0 or tgt_rank < 0:
            continue
        if src_rank > tgt_rank:
            violations.append(
                {
                    "from_module": src_mod,
                    "to_module": tgt_mod,
                    "from_layer": src_layer,
                    "to_layer": tgt_layer,
                    "count": edge.get("count", 1),
                }
            )
    return violations
