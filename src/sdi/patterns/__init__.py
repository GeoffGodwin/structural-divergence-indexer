"""Pattern fingerprinting module: catalog construction and entropy measurement.

Public API:
    build_pattern_catalog(records, config, prev_catalog, partition) -> PatternCatalog
    PatternCatalog: complete pattern analysis with entropy measurements
    PatternFingerprint: structural pattern shape identified by normalized AST hash

Stage 4 of the SDI analysis pipeline. Reads FeatureRecords from Stage 1 (parsing),
groups pattern instances by category and structural hash, and produces a PatternCatalog
with per-shape velocity and boundary spread measurements.
"""

from __future__ import annotations

from sdi.patterns.catalog import (
    CategoryStats,
    PatternCatalog,
    ShapeStats,
    build_pattern_catalog,
)
from sdi.patterns.fingerprint import PatternFingerprint, compute_structural_hash

__all__ = [
    "CategoryStats",
    "PatternCatalog",
    "PatternFingerprint",
    "ShapeStats",
    "build_pattern_catalog",
    "compute_structural_hash",
]
