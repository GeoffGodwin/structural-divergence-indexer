"""PatternCatalog construction and data structures.

Provides:
- ShapeStats: statistics for one structural shape (hash) within a category
- CategoryStats: aggregated statistics for one category
- PatternCatalog: complete pattern analysis across all categories
- build_pattern_catalog(): assemble catalog from FeatureRecords
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sdi.config import SDIConfig
from sdi.patterns._fingerprint_cache import get_file_fingerprints
from sdi.patterns.categories import CATEGORY_NAMES, get_category

if TYPE_CHECKING:
    from sdi.detection.leiden import CommunityResult
    from sdi.snapshot.model import FeatureRecord


@dataclass
class ShapeStats:
    """Statistics for one structural shape (unique hash) within a category.

    Args:
        structural_hash: Normalized AST hash identifying this shape.
        instance_count: Total occurrences of this shape in the current catalog.
        file_paths: File paths that contain at least one instance of this shape.
        velocity: Delta in instance_count vs previous catalog. None on first snapshot.
        boundary_spread: Count of distinct cluster IDs this shape spans. None if
            no community partition was provided.
    """

    structural_hash: str
    instance_count: int
    file_paths: list[str]
    velocity: int | None
    boundary_spread: int | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "structural_hash": self.structural_hash,
            "instance_count": self.instance_count,
            "file_paths": sorted(set(self.file_paths)),
            "velocity": self.velocity,
            "boundary_spread": self.boundary_spread,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShapeStats:
        """Deserialize from a plain dict."""
        return cls(
            structural_hash=data["structural_hash"],
            instance_count=data["instance_count"],
            file_paths=list(data.get("file_paths", [])),
            velocity=data.get("velocity"),
            boundary_spread=data.get("boundary_spread"),
        )


@dataclass
class CategoryStats:
    """Aggregated statistics for one pattern category.

    Args:
        name: Category name (e.g., "error_handling").
        shapes: Mapping of structural_hash -> ShapeStats for all detected shapes.
    """

    name: str
    shapes: dict[str, ShapeStats]

    @property
    def entropy(self) -> int:
        """Count of distinct structural shapes in this category."""
        return len(self.shapes)

    @property
    def canonical_hash(self) -> str | None:
        """Hash of the most frequent shape, or None if no shapes exist."""
        if not self.shapes:
            return None
        return max(self.shapes.values(), key=lambda s: s.instance_count).structural_hash

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "name": self.name,
            "entropy": self.entropy,
            "canonical_hash": self.canonical_hash,
            "shapes": {h: s.to_dict() for h, s in self.shapes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryStats:
        """Deserialize from a plain dict."""
        shapes = {h: ShapeStats.from_dict(sd) for h, sd in data.get("shapes", {}).items()}
        return cls(name=data["name"], shapes=shapes)


@dataclass
class PatternCatalog:
    """Complete pattern analysis across all categories.

    Serializes to/from JSON for inclusion in snapshot files. The serialization
    format is part of the snapshot schema — changes are versioned.

    Args:
        categories: Mapping of category name -> CategoryStats.
    """

    categories: dict[str, CategoryStats]

    def get_category(self, name: str) -> CategoryStats | None:
        """Return CategoryStats for a category name, or None if absent.

        Args:
            name: Category name to look up.

        Returns:
            CategoryStats, or None for unknown or uncatalogued categories.
        """
        return self.categories.get(name)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        category_languages = {
            name: sorted(defn.languages) for name in self.categories if (defn := get_category(name)) is not None
        }
        return {
            "categories": {name: cat.to_dict() for name, cat in self.categories.items()},
            "category_languages": category_languages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PatternCatalog:
        """Deserialize from a plain dict (as produced by to_dict)."""
        categories = {name: CategoryStats.from_dict(cd) for name, cd in data.get("categories", {}).items()}
        return cls(categories=categories)


def _build_partition_lookup(partition: CommunityResult) -> dict[str, int]:
    """Build a file_path -> cluster_id mapping from a CommunityResult.

    Args:
        partition: Community detection result with vertex_names and partition lists.

    Returns:
        Dict mapping each vertex name (file path) to its cluster ID.
    """
    return {name: partition.partition[i] for i, name in enumerate(partition.vertex_names)}


def build_pattern_catalog(
    records: list[FeatureRecord],
    config: SDIConfig,
    prev_catalog: PatternCatalog | None,
    partition: CommunityResult | None,
    cache_dir: Path | None = None,
) -> PatternCatalog:
    """Build a PatternCatalog from a list of FeatureRecords.

    Reads pattern_instances from each FeatureRecord, applies the min_pattern_nodes
    filter, groups instances by (category, structural_hash), then computes per-shape
    velocity and boundary spread. Uses the fingerprint cache (keyed by file content
    hash) when cache_dir is provided.

    Args:
        records: Parsed feature records from Stage 1 (tree-sitter parsing).
        config: SDI configuration; uses config.patterns.min_pattern_nodes.
        prev_catalog: Previous snapshot's PatternCatalog for velocity computation.
            If None, all velocity values are null (first snapshot).
        partition: Community detection result for boundary spread computation.
            If None, all boundary_spread values are null.
        cache_dir: Root cache directory for fingerprint caching, or None to skip.

    Returns:
        PatternCatalog with entropy, canonical, velocity, and boundary spread
        populated for all detected (and all built-in) categories.
    """
    min_nodes: int = config.patterns.min_pattern_nodes

    # raw[category][hash] = {"count": int, "files": list[str]}
    raw: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(lambda: {"count": 0, "files": []}))

    for record in records:
        record_lang = record.language
        for fp in get_file_fingerprints(record, min_nodes, cache_dir):
            cat_def = get_category(fp.category)
            # Non-empty languages set restricts which languages may contribute.
            # Empty set means "applies to all" — no filtering applied.
            if cat_def is not None and cat_def.languages and record_lang not in cat_def.languages:
                continue
            entry = raw[fp.category][fp.structural_hash]
            entry["count"] += 1
            entry["files"].append(record.file_path)

    name_to_cluster: dict[str, int] = _build_partition_lookup(partition) if partition is not None else {}

    # Include all seven built-in categories, plus any extras found in records.
    all_names = list(CATEGORY_NAMES) + [cat for cat in raw if cat not in CATEGORY_NAMES]

    categories: dict[str, CategoryStats] = {}
    for cat_name in all_names:
        shapes_data = raw.get(cat_name, {})
        prev_cat = prev_catalog.get_category(cat_name) if prev_catalog else None
        shapes: dict[str, ShapeStats] = {}

        for hash_val, data in shapes_data.items():
            velocity = _compute_velocity(hash_val, data["count"], prev_catalog, prev_cat)
            boundary_spread = _compute_boundary_spread(data["files"], name_to_cluster, partition)
            shapes[hash_val] = ShapeStats(
                structural_hash=hash_val,
                instance_count=data["count"],
                file_paths=data["files"],
                velocity=velocity,
                boundary_spread=boundary_spread,
            )

        categories[cat_name] = CategoryStats(name=cat_name, shapes=shapes)

    return PatternCatalog(categories=categories)


def _compute_velocity(
    hash_val: str,
    current_count: int,
    prev_catalog: PatternCatalog | None,
    prev_cat: CategoryStats | None,
) -> int | None:
    """Compute velocity (instance count delta) for a shape.

    Args:
        hash_val: Structural hash of the shape.
        current_count: Instance count in the current catalog.
        prev_catalog: Previous catalog (None → first snapshot, velocity is null).
        prev_cat: Previous CategoryStats for the same category (may be None).

    Returns:
        Integer delta (current - prev), or None if no previous catalog.
    """
    if prev_catalog is None:
        return None
    prev_count = prev_cat.shapes[hash_val].instance_count if prev_cat and hash_val in prev_cat.shapes else 0
    return current_count - prev_count


def _compute_boundary_spread(
    file_paths: list[str],
    name_to_cluster: dict[str, int],
    partition: CommunityResult | None,
) -> int | None:
    """Count distinct cluster IDs spanned by a set of file paths.

    Args:
        file_paths: Files containing instances of a shape.
        name_to_cluster: Map from file path to cluster ID.
        partition: Community result (None → spread is null).

    Returns:
        Count of distinct clusters, or None if no partition provided.
    """
    if partition is None:
        return None
    clusters = {name_to_cluster[fp] for fp in file_paths if fp in name_to_cluster}
    return len(clusters)
