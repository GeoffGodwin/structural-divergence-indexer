"""Snapshot assembly from pipeline stage outputs.

assemble_snapshot() is the Stage 5 entry point. It takes the outputs of
Stages 1-4 (parsing, graph, detection, patterns), computes the DivergenceSummary,
writes the snapshot atomically, enforces retention, and returns the Snapshot.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sdi.parsing._parse_cache import cleanup_orphan_parse_cache
from sdi.patterns._fingerprint_cache import cleanup_orphan_fingerprint_cache
from sdi.snapshot.delta import compute_delta
from sdi.snapshot.model import SNAPSHOT_VERSION, Snapshot
from sdi.snapshot.storage import (
    enforce_retention,
    list_snapshots,
    read_snapshot,
    write_snapshot,
)

if TYPE_CHECKING:
    from sdi.config import SDIConfig
    from sdi.detection.leiden import CommunityResult
    from sdi.patterns.catalog import PatternCatalog
    from sdi.snapshot.model import FeatureRecord


def _compute_config_hash(config: SDIConfig) -> str:
    """Hash the analysis-affecting config values.

    Only includes settings that change what the analysis produces, not
    output formatting or retention settings.

    Args:
        config: Fully resolved SDI configuration.

    Returns:
        16-character hex string derived from SHA-256 of the canonical config.
    """
    analysis_cfg = {
        "core": {
            "languages": config.core.languages,
            "exclude": sorted(config.core.exclude),
            "random_seed": config.core.random_seed,
        },
        "boundaries": {
            "leiden_gamma": config.boundaries.leiden_gamma,
            "stability_threshold": config.boundaries.stability_threshold,
            "weighted_edges": config.boundaries.weighted_edges,
        },
        "patterns": {
            "categories": config.patterns.categories,
            "min_pattern_nodes": config.patterns.min_pattern_nodes,
        },
    }
    canonical = json.dumps(analysis_cfg, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _language_breakdown(records: list[FeatureRecord]) -> dict[str, int]:
    """Count files per language from a list of feature records.

    Args:
        records: Parsed feature records from Stage 1.

    Returns:
        Dict mapping language name to file count.
    """
    breakdown: dict[str, int] = {}
    for record in records:
        breakdown[record.language] = breakdown.get(record.language, 0) + 1
    return breakdown


def _partition_data(community: CommunityResult | None) -> dict[str, Any]:
    """Serialize a CommunityResult to a JSON-safe dict for snapshot storage.

    Args:
        community: Community detection result, or None if detection was skipped.

    Returns:
        Dict with partition, vertex_names, inter_cluster_edges, cluster_count,
        and stability_score. Empty dict if community is None.
    """
    if community is None:
        return {}
    return {
        "partition": list(community.partition),
        "vertex_names": list(community.vertex_names),
        "inter_cluster_edges": list(community.inter_cluster_edges),
        "cluster_count": community.cluster_count,
        "stability_score": community.stability_score,
    }


def assemble_snapshot(
    records: list[FeatureRecord],
    graph_metrics: dict[str, Any],
    community: CommunityResult | None,
    catalog: PatternCatalog,
    config: SDIConfig,
    commit_sha: str | None,
    timestamp: str,
    repo_root: Path,
) -> Snapshot:
    """Assemble a Snapshot from all pipeline stage outputs.

    Loads the most recent existing snapshot for delta computation.
    Writes the new snapshot atomically and enforces retention immediately.

    Args:
        records: Feature records from Stage 1 (tree-sitter parsing).
        graph_metrics: Pre-computed graph metrics dict from Stage 2.
        community: Community detection result from Stage 3, or None.
        catalog: Pattern catalog from Stage 4.
        config: Fully resolved SDI configuration.
        commit_sha: Git commit SHA, or None if not in a git repository.
        timestamp: ISO 8601 UTC timestamp string for this snapshot.
        repo_root: Repository root directory (used to resolve config.snapshots.dir).

    Returns:
        The fully assembled and persisted Snapshot.
    """
    snapshots_dir = repo_root / config.snapshots.dir
    if not snapshots_dir.resolve().is_relative_to(repo_root.resolve()):
        msg = f"snapshots.dir resolves outside repository root: {snapshots_dir}"
        raise SystemExit(2, msg)
    config_hash = _compute_config_hash(config)

    catalog_dict = catalog.to_dict()
    part_dict = _partition_data(community)
    _attach_intent_divergence(part_dict, config, repo_root)

    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp=timestamp,
        commit_sha=commit_sha,
        config_hash=config_hash,
        divergence=_null_divergence(),
        file_count=len(records),
        language_breakdown=_language_breakdown(records),
        feature_records=list(records),
        graph_metrics=graph_metrics,
        pattern_catalog=catalog_dict,
        partition_data=part_dict,
    )

    previous = _load_previous(snapshots_dir)
    snap.divergence = compute_delta(snap, previous)

    write_snapshot(snap, snapshots_dir)
    enforce_retention(snapshots_dir, config.snapshots.retention)

    cache_dir = repo_root / ".sdi" / "cache"
    active_hashes = {r.content_hash for r in records if r.content_hash}
    _cleanup_caches(cache_dir, active_hashes)

    return snap


def _attach_intent_divergence(
    part_dict: dict[str, Any],
    config: SDIConfig,
    repo_root: Path,
) -> None:
    """Compute and attach intent divergence to partition_data if a spec exists.

    Modifies part_dict in-place by adding an 'intent_divergence' key when
    a boundary spec is found at config.boundaries.spec_file. Does nothing if
    the spec is absent or partition_data is empty.

    Args:
        part_dict: Mutable partition dict (from _partition_data).
        config: SDI configuration for spec file path.
        repo_root: Repository root for resolving spec_file path.
    """
    if not part_dict:
        return
    spec_path = repo_root / config.boundaries.spec_file
    from sdi.detection.boundaries import compute_intent_divergence, load_boundary_spec

    spec = load_boundary_spec(spec_path)
    if spec is not None:
        intent_div = compute_intent_divergence(spec, part_dict)
        part_dict["intent_divergence"] = intent_div.to_dict()


def _cleanup_caches(cache_dir: Path, active_hashes: set[str]) -> None:
    """Remove orphan parse and fingerprint cache entries after a snapshot.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        active_hashes: Content hashes of all files processed in this run.
    """
    cleanup_orphan_parse_cache(cache_dir, active_hashes)
    cleanup_orphan_fingerprint_cache(cache_dir, active_hashes)


def _null_divergence() -> Any:
    """Return an empty DivergenceSummary (placeholder before delta computation)."""
    from sdi.snapshot.model import DivergenceSummary

    return DivergenceSummary()


def _load_previous(snapshots_dir: Path) -> Snapshot | None:
    """Load the most recent snapshot from disk for delta computation.

    Args:
        snapshots_dir: Directory containing snapshot JSON files.

    Returns:
        The most recent Snapshot, or None if no snapshots exist.
    """
    paths = list_snapshots(snapshots_dir)
    if not paths:
        return None
    return read_snapshot(paths[-1])
