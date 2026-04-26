"""Unit tests for PatternCatalog, CategoryStats, ShapeStats, and build_pattern_catalog."""

from __future__ import annotations

import json

import pytest

from sdi.config import SDIConfig
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


def make_instance(category: str, ast_hash: str, line: int = 1) -> dict:
    """Build a minimal pattern_instance dict."""
    return {
        "category": category,
        "ast_hash": ast_hash,
        "location": {"line": line, "col": 0},
    }


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


# ---------------------------------------------------------------------------
# CategoryStats — entropy, canonical_hash
# ---------------------------------------------------------------------------


def test_entropy_counts_distinct_shapes():
    """CategoryStats.entropy returns the count of distinct shape hashes."""
    shapes = {
        "h1": ShapeStats("h1", 5, [], None, None),
        "h2": ShapeStats("h2", 3, [], None, None),
        "h3": ShapeStats("h3", 1, [], None, None),
    }
    cat = CategoryStats(name="error_handling", shapes=shapes)
    assert cat.entropy == 3


def test_entropy_zero_for_empty_category():
    """An empty category has entropy 0, not an error."""
    cat = CategoryStats(name="error_handling", shapes={})
    assert cat.entropy == 0


def test_canonical_hash_is_most_frequent():
    """Canonical hash belongs to the shape with the highest instance count."""
    shapes = {
        "h1": ShapeStats("h1", 2, [], None, None),
        "h2": ShapeStats("h2", 7, [], None, None),  # most frequent
        "h3": ShapeStats("h3", 1, [], None, None),
    }
    cat = CategoryStats(name="error_handling", shapes=shapes)
    assert cat.canonical_hash == "h2"


def test_canonical_hash_none_for_empty_category():
    """Empty category returns None for canonical_hash."""
    cat = CategoryStats(name="error_handling", shapes={})
    assert cat.canonical_hash is None


# ---------------------------------------------------------------------------
# build_pattern_catalog — grouping and basic structure
# ---------------------------------------------------------------------------


def test_catalog_groups_by_category(two_shape_records: list[FeatureRecord]):
    """Catalog assigns instances to the correct category."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    assert "hash_eh_1" in eh_cat.shapes
    assert "hash_eh_2" in eh_cat.shapes


def test_catalog_counts_instances_correctly(two_shape_records: list[FeatureRecord]):
    """Instance count per shape is correct."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat.shapes["hash_eh_1"].instance_count == 2
    assert eh_cat.shapes["hash_eh_2"].instance_count == 1


def test_catalog_includes_all_builtin_categories(two_shape_records: list[FeatureRecord]):
    """Catalog always includes all seven built-in categories."""
    from sdi.patterns.categories import CATEGORY_NAMES

    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    for cat_name in CATEGORY_NAMES:
        assert cat_name in catalog.categories


def test_empty_category_has_entropy_zero(two_shape_records: list[FeatureRecord]):
    """Categories with no detected instances have entropy 0, not an error."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    logging_cat = catalog.get_category("logging")
    assert logging_cat is not None
    assert logging_cat.entropy == 0


def test_min_pattern_nodes_filters_instances():
    """Instances with node_count below min_pattern_nodes are excluded."""
    records = [
        make_record(
            "src/a.py",
            [
                {
                    "category": "error_handling",
                    "ast_hash": "eh_hash_001",
                    "location": {"line": 1, "col": 0},
                    "node_count": 2,  # below threshold of 5
                }
            ],
        )
    ]
    cfg = SDIConfig()
    cfg.patterns.min_pattern_nodes = 5
    catalog = build_pattern_catalog(records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    assert eh_cat.entropy == 0


# ---------------------------------------------------------------------------
# PatternCatalog serialization — JSON round-trip
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_catalog() -> PatternCatalog:
    """A PatternCatalog with two error_handling shapes."""
    shapes = {
        "hash_a": ShapeStats("hash_a", 3, ["src/a.py", "src/b.py"], None, None),
        "hash_b": ShapeStats("hash_b", 1, ["src/c.py"], None, None),
    }
    cat = CategoryStats(name="error_handling", shapes=shapes)
    return PatternCatalog(categories={"error_handling": cat})


def test_catalog_json_round_trip(simple_catalog: PatternCatalog):
    """PatternCatalog serializes to dict and deserializes back without data loss."""
    data = simple_catalog.to_dict()
    restored = PatternCatalog.from_dict(data)

    orig_cat = simple_catalog.get_category("error_handling")
    rest_cat = restored.get_category("error_handling")
    assert orig_cat is not None and rest_cat is not None
    assert rest_cat.entropy == orig_cat.entropy
    assert rest_cat.canonical_hash == orig_cat.canonical_hash

    for hash_val, orig_shape in orig_cat.shapes.items():
        rest_shape = rest_cat.shapes[hash_val]
        assert rest_shape.instance_count == orig_shape.instance_count
        assert rest_shape.velocity == orig_shape.velocity
        assert rest_shape.boundary_spread == orig_shape.boundary_spread


def test_catalog_to_dict_is_json_serializable(simple_catalog: PatternCatalog):
    """to_dict() output can be round-tripped through json.dumps / json.loads."""
    data = simple_catalog.to_dict()
    json_str = json.dumps(data)
    restored_data = json.loads(json_str)
    restored = PatternCatalog.from_dict(restored_data)
    assert restored.get_category("error_handling") is not None


def test_empty_catalog_round_trip():
    """An empty PatternCatalog serializes and deserializes without error."""
    catalog = PatternCatalog(categories={})
    data = catalog.to_dict()
    restored = PatternCatalog.from_dict(data)
    assert restored.categories == {}


# ---------------------------------------------------------------------------
# M16: language-scope filtering and category_languages in to_dict
# ---------------------------------------------------------------------------


def make_shell_record(file_path: str, instances: list[dict]) -> FeatureRecord:
    """Build a FeatureRecord with language='shell'."""
    return FeatureRecord(
        file_path=file_path,
        language="shell",
        imports=[],
        symbols=[],
        pattern_instances=instances,
        lines_of_code=5,
    )


def test_class_hierarchy_filtered_from_shell_record():
    """build_pattern_catalog silently drops class_hierarchy instances from shell files."""
    records = [
        make_shell_record(
            "deploy.sh",
            [make_instance("class_hierarchy", "hash_shell_class")],
        )
    ]
    cfg = default_config()
    catalog = build_pattern_catalog(records, cfg, None, None)
    ch_cat = catalog.get_category("class_hierarchy")
    assert ch_cat is not None
    assert ch_cat.entropy == 0, "class_hierarchy fingerprints from shell files should be silently dropped"


def test_error_handling_accepted_from_shell_record():
    """build_pattern_catalog accepts error_handling instances from shell files."""
    records = [
        make_shell_record(
            "ci.sh",
            [make_instance("error_handling", "hash_set_e")],
        )
    ]
    cfg = default_config()
    catalog = build_pattern_catalog(records, cfg, None, None)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    assert eh_cat.entropy == 1


def test_category_languages_in_to_dict(simple_catalog: PatternCatalog):
    """to_dict includes category_languages with sorted lists."""
    data = simple_catalog.to_dict()
    assert "category_languages" in data
    cat_langs = data["category_languages"]
    assert "error_handling" in cat_langs
    langs = cat_langs["error_handling"]
    assert isinstance(langs, list)
    assert langs == sorted(langs), "category_languages lists must be sorted"


def test_category_languages_round_trip(two_shape_records: list[FeatureRecord]):
    """category_languages survives a to_dict / from_dict / to_dict round-trip."""
    cfg = default_config()
    catalog = build_pattern_catalog(two_shape_records, cfg, None, None)
    d1 = catalog.to_dict()
    restored = PatternCatalog.from_dict(d1)
    d2 = restored.to_dict()
    assert d1["category_languages"] == d2["category_languages"]
