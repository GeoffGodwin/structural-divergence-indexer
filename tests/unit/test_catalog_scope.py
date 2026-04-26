"""Unit tests for patterns.scope_exclude filtering in build_pattern_catalog (M17)."""

from __future__ import annotations

import pytest

from sdi.config import SDIConfig
from sdi.patterns.catalog import PatternCatalog, build_pattern_catalog
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


def config_with_scope(patterns: list[str]) -> SDIConfig:
    """Return SDIConfig with given scope_exclude and min_pattern_nodes=1."""
    cfg = SDIConfig()
    cfg.patterns.min_pattern_nodes = 1
    cfg.patterns.scope_exclude = patterns
    return cfg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mixed_records() -> list[FeatureRecord]:
    """Records from src/ and tests/ with distinct error_handling shapes each."""
    return [
        make_record("src/a.py", [make_instance("error_handling", "hash_src_a")]),
        make_record("src/b.py", [make_instance("error_handling", "hash_src_b")]),
        make_record("tests/foo.py", [make_instance("error_handling", "hash_test_foo")]),
        make_record("tests/sub/bar.py", [make_instance("error_handling", "hash_test_bar")]),
    ]


# ---------------------------------------------------------------------------
# Filtering — records matching scope_exclude are excluded from Stage 4
# ---------------------------------------------------------------------------


def test_scope_exclude_removes_matched_records(mixed_records: list[FeatureRecord]) -> None:
    """Records matching scope_exclude do not contribute to the pattern catalog."""
    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    eh = catalog.get_category("error_handling")
    assert eh is not None
    all_file_paths = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert not any(fp.startswith("tests/") for fp in all_file_paths)


def test_scope_exclude_keeps_unmatched_records(mixed_records: list[FeatureRecord]) -> None:
    """Records NOT matching scope_exclude still appear in the catalog."""
    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    eh = catalog.get_category("error_handling")
    assert eh is not None
    all_file_paths = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert "src/a.py" in all_file_paths
    assert "src/b.py" in all_file_paths


def test_scope_exclude_reduces_entropy(mixed_records: list[FeatureRecord]) -> None:
    """Excluding test records reduces entropy from 4 to 2 distinct shapes."""
    cfg_all = config_with_scope([])
    catalog_all = build_pattern_catalog(mixed_records, cfg_all, None, None)
    cfg_excl = config_with_scope(["tests/**"])
    catalog_excl = build_pattern_catalog(mixed_records, cfg_excl, None, None)
    assert catalog_excl.get_category("error_handling").entropy < catalog_all.get_category("error_handling").entropy


def test_meta_scope_excluded_file_count(mixed_records: list[FeatureRecord]) -> None:
    """meta.scope_excluded_file_count equals the number of excluded records."""
    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    assert catalog.meta.get("scope_excluded_file_count") == 2


def test_meta_absent_when_no_exclusion(mixed_records: list[FeatureRecord]) -> None:
    """meta block is absent from to_dict() when scope_exclude is empty."""
    cfg = config_with_scope([])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    data = catalog.to_dict()
    assert "meta" not in data


def test_meta_present_in_to_dict_when_excluded(mixed_records: list[FeatureRecord]) -> None:
    """meta block appears in to_dict() when files were excluded."""
    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    data = catalog.to_dict()
    assert "meta" in data
    assert data["meta"]["scope_excluded_file_count"] == 2


# ---------------------------------------------------------------------------
# Glob semantics
# ---------------------------------------------------------------------------


def test_glob_wildcard_any_depth() -> None:
    """tests/** matches tests/foo.py and tests/sub/bar.py but not nottests/foo.py."""
    records = [
        make_record("tests/foo.py", [make_instance("error_handling", "h1")]),
        make_record("tests/sub/bar.py", [make_instance("error_handling", "h2")]),
        make_record("nottests/foo.py", [make_instance("error_handling", "h3")]),
    ]
    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(records, cfg, None, None)
    eh = catalog.get_category("error_handling")
    all_fps = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert "nottests/foo.py" in all_fps
    assert "tests/foo.py" not in all_fps
    assert "tests/sub/bar.py" not in all_fps


def test_glob_double_star_extension() -> None:
    """**/*.test.ts matches src/foo.test.ts but not src/foo.ts."""
    records = [
        make_record("src/foo.test.ts", [make_instance("error_handling", "h1")]),
        make_record("src/util/bar.test.ts", [make_instance("error_handling", "h2")]),
        make_record("src/foo.ts", [make_instance("error_handling", "h3")]),
    ]
    cfg = config_with_scope(["**/*.test.ts"])
    catalog = build_pattern_catalog(records, cfg, None, None)
    assert catalog.meta.get("scope_excluded_file_count") == 2
    eh = catalog.get_category("error_handling")
    all_fps = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert "src/foo.ts" in all_fps
    assert "src/foo.test.ts" not in all_fps


def test_glob_anchored_path() -> None:
    """/scripts/setup.sh (anchored) matches only top-level scripts/setup.sh."""
    records = [
        make_record("scripts/setup.sh", [make_instance("error_handling", "h1")]),
        make_record("lib/scripts/setup.sh", [make_instance("error_handling", "h2")]),
    ]
    cfg = config_with_scope(["/scripts/setup.sh"])
    catalog = build_pattern_catalog(records, cfg, None, None)
    eh = catalog.get_category("error_handling")
    all_fps = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert "lib/scripts/setup.sh" in all_fps
    assert "scripts/setup.sh" not in all_fps


# ---------------------------------------------------------------------------
# PatternCatalog.from_dict backward compatibility
# ---------------------------------------------------------------------------


def test_from_dict_without_meta_key() -> None:
    """Deserializing a catalog dict without 'meta' produces empty meta dict."""
    data = {
        "categories": {},
        "category_languages": {},
    }
    catalog = PatternCatalog.from_dict(data)
    assert catalog.meta == {}


def test_from_dict_with_meta_key() -> None:
    """Deserializing a catalog dict with 'meta' restores the meta dict."""
    data = {
        "categories": {},
        "category_languages": {},
        "meta": {"scope_excluded_file_count": 5},
    }
    catalog = PatternCatalog.from_dict(data)
    assert catalog.meta == {"scope_excluded_file_count": 5}


# ---------------------------------------------------------------------------
# 100% exclusion edge case
# ---------------------------------------------------------------------------


def test_all_files_excluded_produces_empty_shapes(mixed_records: list[FeatureRecord]) -> None:
    """When scope_exclude matches every record, all category shapes are empty."""
    # "**" matches every file path.
    cfg = config_with_scope(["**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    for cat_name, cat_stats in catalog.categories.items():
        assert cat_stats.shapes == {}, f"Category '{cat_name}' should have no shapes when all files are excluded"


def test_all_files_excluded_meta_count_equals_total(mixed_records: list[FeatureRecord]) -> None:
    """meta.scope_excluded_file_count equals total record count under 100% exclusion."""
    cfg = config_with_scope(["**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    assert catalog.meta.get("scope_excluded_file_count") == len(mixed_records)


def test_all_files_excluded_entropy_is_zero(mixed_records: list[FeatureRecord]) -> None:
    """Entropy for every category is 0 when all files are excluded."""
    cfg = config_with_scope(["**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    for cat_stats in catalog.categories.values():
        assert cat_stats.entropy == 0


def test_all_files_excluded_canonical_hash_is_none(mixed_records: list[FeatureRecord]) -> None:
    """canonical_hash for every category is None when all files are excluded."""
    cfg = config_with_scope(["**"])
    catalog = build_pattern_catalog(mixed_records, cfg, None, None)
    for cat_stats in catalog.categories.values():
        assert cat_stats.canonical_hash is None


# ---------------------------------------------------------------------------
# Windows-path normalization (backslash → forward-slash before matching)
# ---------------------------------------------------------------------------


def test_windows_path_backslash_excluded_by_scope() -> None:
    """A record with a Windows-style backslash path is correctly excluded by scope_exclude.

    catalog.py:201 calls r.file_path.replace('\\\\', '/') before pathspec.match_file().
    This test exercises that branch: if normalization is absent the backslash path
    would not match the gitignore pattern and the record would escape exclusion.
    """
    win_path_record = make_record("tests\\sub\\bar.py", [make_instance("error_handling", "hash_win")])
    posix_record = make_record("src/main.py", [make_instance("error_handling", "hash_posix")])
    records = [win_path_record, posix_record]

    cfg = config_with_scope(["tests/**"])
    catalog = build_pattern_catalog(records, cfg, None, None)

    # The Windows-path record should be excluded (normalized to tests/sub/bar.py).
    assert catalog.meta.get("scope_excluded_file_count") == 1

    eh = catalog.get_category("error_handling")
    assert eh is not None
    all_fps = {fp for shape in eh.shapes.values() for fp in shape.file_paths}
    assert "src/main.py" in all_fps
    # The raw file_path stored in ShapeStats uses the original string, so check
    # the Windows-path variant is absent entirely.
    assert "tests\\sub\\bar.py" not in all_fps
