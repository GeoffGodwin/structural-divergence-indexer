"""Tests that shared conftest fixtures match the real FeatureRecord schema.

The sample_feature_record fixture historically used the wrong keys for
pattern_instances ({"type": ...} instead of {"category", "ast_hash", "location"}).
These tests guard against that regression and validate schema conformance.
"""

from __future__ import annotations

import pytest

from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# sample_feature_record — pattern_instances schema correctness
# ---------------------------------------------------------------------------

class TestSampleFeatureRecordPatternInstances:
    def test_pattern_instances_have_category_key(self, sample_feature_record: FeatureRecord) -> None:
        """Every pattern instance must have a 'category' key."""
        for instance in sample_feature_record.pattern_instances:
            assert "category" in instance, (
                f"pattern_instances entry missing 'category': {instance}"
            )

    def test_pattern_instances_have_no_type_key(self, sample_feature_record: FeatureRecord) -> None:
        """'type' is not a valid key in pattern_instances — it was the old incorrect schema."""
        for instance in sample_feature_record.pattern_instances:
            assert "type" not in instance, (
                f"pattern_instances entry uses stale 'type' key: {instance}"
            )

    def test_pattern_instances_have_ast_hash_key(self, sample_feature_record: FeatureRecord) -> None:
        """Every pattern instance must have an 'ast_hash' key."""
        for instance in sample_feature_record.pattern_instances:
            assert "ast_hash" in instance, (
                f"pattern_instances entry missing 'ast_hash': {instance}"
            )

    def test_pattern_instances_have_location_key(self, sample_feature_record: FeatureRecord) -> None:
        """Every pattern instance must have a 'location' key."""
        for instance in sample_feature_record.pattern_instances:
            assert "location" in instance, (
                f"pattern_instances entry missing 'location': {instance}"
            )

    def test_pattern_instances_location_has_line_and_col(self, sample_feature_record: FeatureRecord) -> None:
        """The 'location' dict must contain 'line' and 'col' integer keys."""
        for instance in sample_feature_record.pattern_instances:
            location = instance["location"]
            assert "line" in location, f"location missing 'line': {location}"
            assert "col" in location, f"location missing 'col': {location}"
            assert isinstance(location["line"], int), (
                f"location['line'] must be int, got {type(location['line'])}"
            )
            assert isinstance(location["col"], int), (
                f"location['col'] must be int, got {type(location['col'])}"
            )

    def test_pattern_instances_category_is_known_value(self, sample_feature_record: FeatureRecord) -> None:
        """Category values must come from the known set produced by the Python adapter."""
        valid_categories = {"error_handling", "logging", "data_access"}
        for instance in sample_feature_record.pattern_instances:
            assert instance["category"] in valid_categories, (
                f"Unknown category '{instance['category']}' — expected one of {valid_categories}"
            )

    def test_pattern_instances_ast_hash_is_8_char_hex(self, sample_feature_record: FeatureRecord) -> None:
        """ast_hash must be an 8-character lowercase hex string (matching _structural_hash output)."""
        for instance in sample_feature_record.pattern_instances:
            ast_hash = instance["ast_hash"]
            assert isinstance(ast_hash, str), f"ast_hash must be str, got {type(ast_hash)}"
            assert len(ast_hash) == 8, f"ast_hash must be 8 chars, got '{ast_hash}' (len={len(ast_hash)})"
            assert all(c in "0123456789abcdef" for c in ast_hash), (
                f"ast_hash must be lowercase hex, got '{ast_hash}'"
            )

    def test_pattern_instances_is_list(self, sample_feature_record: FeatureRecord) -> None:
        """pattern_instances must be a list, not empty (fixture has at least one entry)."""
        assert isinstance(sample_feature_record.pattern_instances, list)
        assert len(sample_feature_record.pattern_instances) >= 1


# ---------------------------------------------------------------------------
# sample_feature_record — basic FeatureRecord field correctness
# ---------------------------------------------------------------------------

class TestSampleFeatureRecordFields:
    def test_file_path_is_string(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.file_path, str)
        assert sample_feature_record.file_path != ""

    def test_language_is_string(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.language, str)
        assert sample_feature_record.language != ""

    def test_imports_is_list_of_strings(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.imports, list)
        for imp in sample_feature_record.imports:
            assert isinstance(imp, str)

    def test_symbols_is_list_of_strings(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.symbols, list)
        for sym in sample_feature_record.symbols:
            assert isinstance(sym, str)

    def test_lines_of_code_is_positive_int(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.lines_of_code, int)
        assert sample_feature_record.lines_of_code > 0

    def test_round_trip_serialization_preserves_pattern_instances(
        self, sample_feature_record: FeatureRecord
    ) -> None:
        """to_dict() / from_dict() must preserve the full pattern_instances schema."""
        as_dict = sample_feature_record.to_dict()
        restored = FeatureRecord.from_dict(as_dict)
        assert restored.pattern_instances == sample_feature_record.pattern_instances
