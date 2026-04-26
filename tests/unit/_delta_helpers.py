"""Shared helpers for delta unit tests.

Not a test file — this module is imported by test_delta.py and
test_delta_per_language.py to avoid duplicating fixture factories.
"""

from __future__ import annotations

from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, FeatureRecord, Snapshot

INCOMPAT_VERSION = "99.0.0"
OLD_SCHEMA_VERSION = "0.1.0"


def make_snap(
    pattern_catalog: dict | None = None,
    graph_metrics: dict | None = None,
    partition_data: dict | None = None,
    version: str = SNAPSHOT_VERSION,
    feature_records: list | None = None,
    divergence: DivergenceSummary | None = None,
) -> Snapshot:
    return Snapshot(
        snapshot_version=version,
        timestamp="2026-04-10T00:00:00Z",
        commit_sha=None,
        config_hash="test",
        divergence=divergence or DivergenceSummary(),
        file_count=0,
        language_breakdown={},
        graph_metrics=graph_metrics or {},
        pattern_catalog=pattern_catalog or {},
        partition_data=partition_data or {},
        feature_records=feature_records or [],
    )


def catalog(categories: dict[str, list[str]]) -> dict:
    """Minimal serialized PatternCatalog: {category: [hash, ...]}."""
    cats = {}
    for cat_name, hashes in categories.items():
        shapes = {
            h: {
                "structural_hash": h,
                "instance_count": 1,
                "file_paths": ["src/a.py"],
                "velocity": None,
                "boundary_spread": None,
            }
            for h in hashes
        }
        cats[cat_name] = {
            "name": cat_name,
            "entropy": len(hashes),
            "canonical_hash": hashes[0] if hashes else None,
            "shapes": shapes,
        }
    return {"categories": cats}


def catalog_with_files(categories: dict[str, list[tuple[str, str, int]]]) -> dict:
    """Build a catalog dict where shapes reference specific files.

    categories: {cat_name: [(hash, file_path, count), ...]}
    """
    cats = {}
    for cat_name, shapes in categories.items():
        shape_dict: dict = {}
        for h, fp, cnt in shapes:
            if h not in shape_dict:
                shape_dict[h] = {
                    "structural_hash": h,
                    "instance_count": cnt,
                    "file_paths": [fp] * cnt,
                    "velocity": None,
                    "boundary_spread": None,
                }
            else:
                shape_dict[h]["instance_count"] += cnt
                shape_dict[h]["file_paths"].extend([fp] * cnt)
        cats[cat_name] = {
            "name": cat_name,
            "entropy": len(shape_dict),
            "canonical_hash": next(iter(shape_dict)) if shape_dict else None,
            "shapes": shape_dict,
        }
    return {"categories": cats}


def fake_record(file_path: str, language: str) -> FeatureRecord:
    """Minimal FeatureRecord for building file->language maps."""
    return FeatureRecord(
        file_path=file_path,
        language=language,
        imports=[],
        symbols=[],
        pattern_instances=[],
        lines_of_code=0,
    )


def metrics(
    density: float = 0.0,
    hub_concentration: float = 0.0,
    cycle_count: int = 0,
    max_depth: int = 0,
    node_count: int = 10,
) -> dict:
    return {
        "node_count": node_count,
        "edge_count": 0,
        "density": density,
        "cycle_count": cycle_count,
        "hub_concentration": hub_concentration,
        "component_count": 1,
        "max_depth": max_depth,
        "hub_nodes": [],
    }


def partition(inter_edges: list[dict] | None = None) -> dict:
    return {
        "partition": [0, 1],
        "vertex_names": ["src/a.py", "src/b.py"],
        "inter_cluster_edges": inter_edges or [],
        "cluster_count": 2,
        "stability_score": 1.0,
    }
