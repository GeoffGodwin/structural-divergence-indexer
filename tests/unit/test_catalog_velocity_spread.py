"""Unit tests for build_pattern_catalog: velocity, boundary spread, and high-entropy."""

from __future__ import annotations

import pytest

from sdi.config import SDIConfig
from sdi.detection.leiden import CommunityResult
from sdi.patterns.catalog import (
    CategoryStats,
    PatternCatalog,
    ShapeStats,
    build_pattern_catalog,
)
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_record(file_path: str, instances: list[dict]) -> FeatureRecord:
    """Build a FeatureRecord with specific pattern_instances."""
    return FeatureRecord(
        file_path=file_path,
        language="python",
        imports=[],
        symbols=[],
        pattern_instances=instances,
        lines_of_code=10,
    )


def make_instance(category: str, ast_hash: str) -> dict:
    """Build a minimal pattern_instance dict."""
    return {"category": category, "ast_hash": ast_hash, "location": {"line": 1, "col": 0}}


def default_config() -> SDIConfig:
    """Return SDIConfig with min_pattern_nodes=1 (no filtering in unit tests)."""
    cfg = SDIConfig()
    cfg.patterns.min_pattern_nodes = 1
    return cfg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_shape_records() -> list[FeatureRecord]:
    """FeatureRecords with two distinct error_handling shapes."""
    return [
        make_record("src/a.py", [make_instance("error_handling", "hash_eh_1")]),
        make_record("src/b.py", [make_instance("error_handling", "hash_eh_1")]),
        make_record("src/c.py", [make_instance("error_handling", "hash_eh_2")]),
    ]


@pytest.fixture
def high_entropy_records() -> list[FeatureRecord]:
    """FeatureRecords with 4+ distinct error_handling shapes."""
    return [
        make_record("src/m0.py", [make_instance("error_handling", "eh_bare_0001")]),
        make_record("src/m1.py", [make_instance("error_handling", "eh_single_002")]),
        make_record("src/m2.py", [make_instance("error_handling", "eh_multi_003")]),
        make_record("src/m3.py", [make_instance("error_handling", "eh_finally_04")]),
        make_record("src/m4.py", [make_instance("error_handling", "eh_bare_0001")]),
        make_record("src/m5.py", [make_instance("data_access", "da_orm_00001")]),
        make_record("src/m6.py", [make_instance("data_access", "da_cursor_002")]),
        make_record("src/m7.py", [make_instance("data_access", "da_raw_00003")]),
        make_record("src/m8.py", [make_instance("logging", "log_module_01")]),
        make_record("src/m9.py", [make_instance("logging", "log_instance_2")]),
    ]


@pytest.fixture
def simple_partition() -> CommunityResult:
    """A CommunityResult with two clusters over four files."""
    return CommunityResult(
        partition=[0, 0, 1, 1],
        stability_score=1.0,
        cluster_count=2,
        inter_cluster_edges=[],
        surface_area_ratios={0: 0.0, 1: 0.0},
        vertex_names=["src/a.py", "src/b.py", "src/c.py", "src/d.py"],
    )


# ---------------------------------------------------------------------------
# Velocity tests
# ---------------------------------------------------------------------------


def test_velocity_is_null_on_first_snapshot(two_shape_records: list[FeatureRecord]):
    """With no prev_catalog, all shape velocities are None."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    for shape in eh_cat.shapes.values():
        assert shape.velocity is None


def test_velocity_is_delta_vs_previous(two_shape_records: list[FeatureRecord]):
    """Velocity = current instance count minus previous instance count."""
    cfg = default_config()
    prev_shapes = {
        "hash_eh_1": ShapeStats("hash_eh_1", 1, ["src/a.py"], None, None),
    }
    prev_cat_stats = CategoryStats(name="error_handling", shapes=prev_shapes)
    prev_catalog = PatternCatalog(categories={"error_handling": prev_cat_stats})

    catalog = build_pattern_catalog(two_shape_records, cfg, prev_catalog, None)
    eh_cat = catalog.get_category("error_handling")

    # hash_eh_1 went from 1 to 2 → velocity = +1
    assert eh_cat.shapes["hash_eh_1"].velocity == 1
    # hash_eh_2 is new → velocity = 1 - 0 = 1
    assert eh_cat.shapes["hash_eh_2"].velocity == 1


def test_velocity_negative_when_count_decreases():
    """Velocity is negative when a shape's instance count decreases."""
    cfg = default_config()
    records = [make_record("src/a.py", [make_instance("error_handling", "hash_eh_1")])]
    prev_shapes = {"hash_eh_1": ShapeStats("hash_eh_1", 5, ["src/a.py"], None, None)}
    prev_cat_stats = CategoryStats(name="error_handling", shapes=prev_shapes)
    prev_catalog = PatternCatalog(categories={"error_handling": prev_cat_stats})

    catalog = build_pattern_catalog(records, cfg, prev_catalog, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat.shapes["hash_eh_1"].velocity == -4  # 1 - 5


def test_velocity_zero_for_new_shape_in_prev_catalog():
    """A shape appearing for the first time with prev_catalog has velocity = count."""
    cfg = default_config()
    records = [make_record("src/a.py", [make_instance("error_handling", "new_hash")])]
    prev_shapes = {"old_hash": ShapeStats("old_hash", 3, ["src/x.py"], None, None)}
    prev_cat_stats = CategoryStats(name="error_handling", shapes=prev_shapes)
    prev_catalog = PatternCatalog(categories={"error_handling": prev_cat_stats})

    catalog = build_pattern_catalog(records, cfg, prev_catalog, None)
    eh_cat = catalog.get_category("error_handling")
    # new_hash was not in prev → prev_count = 0, velocity = 1 - 0 = 1
    assert eh_cat.shapes["new_hash"].velocity == 1


# ---------------------------------------------------------------------------
# Boundary spread tests
# ---------------------------------------------------------------------------


def test_boundary_spread_null_when_no_partition(two_shape_records: list[FeatureRecord]):
    """With no partition, all boundary_spread values are None."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    for shape in eh_cat.shapes.values():
        assert shape.boundary_spread is None


def test_boundary_spread_counts_distinct_clusters(simple_partition: CommunityResult):
    """boundary_spread = count of distinct clusters spanned by the shape's files."""
    cfg = default_config()
    records = [
        make_record("src/a.py", [make_instance("error_handling", "hash_cross")]),
        make_record("src/c.py", [make_instance("error_handling", "hash_cross")]),
    ]
    catalog = build_pattern_catalog(records, cfg, None, simple_partition)
    eh_cat = catalog.get_category("error_handling")
    # src/a.py → cluster 0, src/c.py → cluster 1
    assert eh_cat.shapes["hash_cross"].boundary_spread == 2


def test_boundary_spread_one_cluster():
    """Shape confined to a single cluster has boundary_spread = 1."""
    partition = CommunityResult(
        partition=[0, 0],
        stability_score=1.0,
        cluster_count=1,
        inter_cluster_edges=[],
        surface_area_ratios={0: 0.0},
        vertex_names=["src/a.py", "src/b.py"],
    )
    records = [
        make_record("src/a.py", [make_instance("error_handling", "hash_single")]),
        make_record("src/b.py", [make_instance("error_handling", "hash_single")]),
    ]
    cfg = default_config()
    catalog = build_pattern_catalog(records, cfg, None, partition)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat.shapes["hash_single"].boundary_spread == 1


# ---------------------------------------------------------------------------
# High-entropy fixture — entropy assertions
# ---------------------------------------------------------------------------


def test_high_entropy_error_handling(high_entropy_records: list[FeatureRecord]):
    """error_handling category must have ≥ 4 distinct shapes."""
    cfg = default_config()
    catalog = build_pattern_catalog(high_entropy_records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    assert eh_cat.entropy >= 4


def test_high_entropy_data_access(high_entropy_records: list[FeatureRecord]):
    """data_access category must have ≥ 3 distinct shapes."""
    cfg = default_config()
    catalog = build_pattern_catalog(high_entropy_records, cfg, None, None)
    da_cat = catalog.get_category("data_access")
    assert da_cat is not None
    assert da_cat.entropy >= 3


def test_high_entropy_logging(high_entropy_records: list[FeatureRecord]):
    """logging category must have ≥ 2 distinct shapes."""
    cfg = default_config()
    catalog = build_pattern_catalog(high_entropy_records, cfg, None, None)
    log_cat = catalog.get_category("logging")
    assert log_cat is not None
    assert log_cat.entropy >= 2
