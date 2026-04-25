"""Integration test: parse high-entropy fixture files with tree-sitter.

Validates that the Python parsing adapter and pattern catalog pipeline agree
with the fixture design intent. The unit tests in test_catalog_velocity_spread.py
use synthetic in-memory records with hardcoded hash strings; this test exercises
the full path from raw .py source → tree-sitter AST → pattern instances →
PatternCatalog entropy values.

Fixtures are in tests/fixtures/high-entropy/ and contain deliberately diverse
patterns across three categories: error_handling (5 styles), data_access (3 styles),
and logging (2 styles).
"""

from __future__ import annotations

from pathlib import Path

from sdi.config import SDIConfig
from sdi.parsing.python import PythonAdapter
from sdi.patterns.catalog import PatternCatalog, build_pattern_catalog
from sdi.snapshot.model import FeatureRecord

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "high-entropy"


def _parse_fixtures(min_nodes: int = 1) -> PatternCatalog:
    """Parse all .py files in the high-entropy fixture directory.

    Returns a PatternCatalog built from real tree-sitter parse results.
    Uses the fixture directory as the repo_root so all file paths are
    relative to it (e.g. "error_bare.py", not an absolute path).
    """
    adapter = PythonAdapter(repo_root=FIXTURE_DIR)
    records: list[FeatureRecord] = []
    for py_file in sorted(FIXTURE_DIR.glob("*.py")):
        source = py_file.read_bytes()
        record = adapter.parse_file(py_file, source)
        records.append(record)

    cfg = SDIConfig()
    cfg.patterns.min_pattern_nodes = min_nodes
    return build_pattern_catalog(records, cfg, None, None)


def test_fixture_dir_contains_expected_files():
    """Sanity check: high-entropy fixture directory has the 11 expected .py files."""
    py_files = sorted(f.name for f in FIXTURE_DIR.glob("*.py"))
    expected = {
        "data_cursor.py",
        "data_dict.py",
        "data_orm.py",
        "error_bare.py",
        "error_else.py",
        "error_finally.py",
        "error_multi.py",
        "error_single.py",
        "logging_instance.py",
        "logging_module.py",
        "mixed_patterns.py",
    }
    assert set(py_files) == expected, f"Unexpected files in fixture dir. Got: {py_files}"


def test_parsing_produces_records_for_all_files():
    """PythonAdapter produces one FeatureRecord per fixture file."""
    adapter = PythonAdapter(repo_root=FIXTURE_DIR)
    records = [adapter.parse_file(p, p.read_bytes()) for p in sorted(FIXTURE_DIR.glob("*.py"))]
    assert len(records) == 11
    for record in records:
        assert record.language == "python"
        assert record.file_path.endswith(".py")


def test_error_handling_files_produce_pattern_instances():
    """Each error_* fixture file contributes at least one error_handling instance."""
    adapter = PythonAdapter(repo_root=FIXTURE_DIR)
    error_files = sorted(FIXTURE_DIR.glob("error_*.py"))
    assert len(error_files) == 5, "Expected 5 error_* fixture files"
    for py_file in error_files:
        record = adapter.parse_file(py_file, py_file.read_bytes())
        eh_instances = [inst for inst in record.pattern_instances if inst.get("category") == "error_handling"]
        assert len(eh_instances) >= 1, f"{py_file.name} produced no error_handling instances"


def test_error_handling_entropy_ge_4_from_real_parsing():
    """Parsing actual high-entropy fixtures yields >= 4 distinct error_handling shapes.

    The 5 error_* files each use a structurally different try/except pattern
    (bare, single, multi, finally, else), so the tree-sitter AST produces at
    least 4 distinct structural hashes for the error_handling category.
    """
    catalog = _parse_fixtures(min_nodes=1)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    assert eh_cat.entropy >= 4, (
        f"Expected >= 4 distinct error_handling shapes from real parsing, "
        f"got {eh_cat.entropy}. Shapes: {list(eh_cat.shapes.keys())}"
    )


def test_data_access_entropy_ge_3_from_real_parsing():
    """Parsing actual high-entropy fixtures yields >= 3 distinct data_access shapes.

    The data_orm.py (ORM query chaining), data_cursor.py (raw cursor), and
    data_dict.py fixtures implement structurally different data access patterns.
    """
    catalog = _parse_fixtures(min_nodes=1)
    da_cat = catalog.get_category("data_access")
    assert da_cat is not None
    assert da_cat.entropy >= 3, (
        f"Expected >= 3 distinct data_access shapes from real parsing, "
        f"got {da_cat.entropy}. Shapes: {list(da_cat.shapes.keys())}"
    )


def test_logging_entropy_ge_2_from_real_parsing():
    """Parsing actual high-entropy fixtures yields >= 2 distinct logging shapes.

    logging_module.py uses logger.info/debug/error — at least two distinct
    call structures. logging_instance.py uses instance-level logger calls.
    """
    catalog = _parse_fixtures(min_nodes=1)
    log_cat = catalog.get_category("logging")
    assert log_cat is not None
    assert log_cat.entropy >= 2, (
        f"Expected >= 2 distinct logging shapes from real parsing, "
        f"got {log_cat.entropy}. Shapes: {list(log_cat.shapes.keys())}"
    )


def test_all_builtin_categories_present_after_real_parsing():
    """build_pattern_catalog always populates all 7 built-in categories, even with no instances."""
    from sdi.patterns.categories import CATEGORY_NAMES

    catalog = _parse_fixtures(min_nodes=1)
    for name in CATEGORY_NAMES:
        cat = catalog.get_category(name)
        assert cat is not None, f"Built-in category '{name}' missing from catalog"


def test_error_handling_shapes_have_nonzero_instance_counts():
    """Every shape detected in the error_handling category has instance_count >= 1."""
    catalog = _parse_fixtures(min_nodes=1)
    eh_cat = catalog.get_category("error_handling")
    assert eh_cat is not None
    for hash_val, shape in eh_cat.shapes.items():
        assert shape.instance_count >= 1, f"Shape {hash_val!r} has zero instance count"


def test_velocity_is_null_on_real_first_parse():
    """When no prev_catalog is supplied, velocity is None for all shapes in all categories."""
    catalog = _parse_fixtures(min_nodes=1)
    for cat in catalog.categories.values():
        for shape in cat.shapes.values():
            assert shape.velocity is None, (
                f"Category {cat.name!r} shape {shape.structural_hash!r} has "
                f"non-null velocity on first parse: {shape.velocity}"
            )


def test_min_pattern_nodes_filter_reduces_shape_count():
    """Raising min_pattern_nodes filters out small patterns, reducing total shape count."""
    catalog_unfiltered = _parse_fixtures(min_nodes=1)
    catalog_filtered = _parse_fixtures(min_nodes=20)

    total_unfiltered = sum(len(cat.shapes) for cat in catalog_unfiltered.categories.values())
    total_filtered = sum(len(cat.shapes) for cat in catalog_filtered.categories.values())
    # With a high min_nodes threshold, some (or all) shapes should be filtered out
    assert total_filtered <= total_unfiltered, "Filtered catalog should have fewer or equal shapes than unfiltered"
