"""Unit tests for sdi.snapshot.model — Snapshot, DivergenceSummary, FeatureRecord."""

from __future__ import annotations

import json

from sdi.parsing import FeatureRecord
from sdi.snapshot.model import (
    SNAPSHOT_VERSION,
    DivergenceSummary,
    Snapshot,
)


class TestFeatureRecordConstruction:
    """FeatureRecord can be constructed and round-trips through dict."""

    def test_construction(self, sample_feature_record: FeatureRecord) -> None:
        assert sample_feature_record.file_path == "src/foo.py"
        assert sample_feature_record.language == "python"
        assert sample_feature_record.lines_of_code == 50

    def test_imports_is_list(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.imports, list)

    def test_symbols_is_list(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.symbols, list)

    def test_pattern_instances_is_list(self, sample_feature_record: FeatureRecord) -> None:
        assert isinstance(sample_feature_record.pattern_instances, list)

    def test_to_dict_round_trip(self, sample_feature_record: FeatureRecord) -> None:
        d = sample_feature_record.to_dict()
        restored = FeatureRecord.from_dict(d)
        assert restored == sample_feature_record

    def test_to_dict_contains_all_fields(self, sample_feature_record: FeatureRecord) -> None:
        d = sample_feature_record.to_dict()
        assert "file_path" in d
        assert "language" in d
        assert "imports" in d
        assert "symbols" in d
        assert "pattern_instances" in d
        assert "lines_of_code" in d


class TestDivergenceSummaryNullDeltas:
    """First snapshot has null deltas — None, not 0."""

    def test_delta_fields_are_none(self, sample_divergence: DivergenceSummary) -> None:
        assert sample_divergence.pattern_entropy_delta is None
        assert sample_divergence.convention_drift_delta is None
        assert sample_divergence.coupling_topology_delta is None
        assert sample_divergence.boundary_violations_delta is None

    def test_current_values_are_set(self, sample_divergence: DivergenceSummary) -> None:
        assert sample_divergence.pattern_entropy == 1.5
        assert sample_divergence.convention_drift == 0.3

    def test_fully_null_divergence(self) -> None:
        d = DivergenceSummary()
        assert d.pattern_entropy is None
        assert d.pattern_entropy_delta is None

    def test_to_dict_preserves_none(self, sample_divergence: DivergenceSummary) -> None:
        d = sample_divergence.to_dict()
        assert d["pattern_entropy_delta"] is None

    def test_from_dict_round_trip(self, sample_divergence: DivergenceSummary) -> None:
        d = sample_divergence.to_dict()
        restored = DivergenceSummary.from_dict(d)
        assert restored == sample_divergence


class TestSnapshotVersionField:
    """snapshot_version must always be present in a Snapshot."""

    def test_version_field_present(self, sample_snapshot: Snapshot) -> None:
        assert hasattr(sample_snapshot, "snapshot_version")

    def test_version_matches_constant(self, sample_snapshot: Snapshot) -> None:
        assert sample_snapshot.snapshot_version == SNAPSHOT_VERSION

    def test_version_in_serialized_dict(self, sample_snapshot: Snapshot) -> None:
        d = sample_snapshot.to_dict()
        assert "snapshot_version" in d

    def test_version_in_json_output(self, sample_snapshot: Snapshot) -> None:
        data = json.loads(sample_snapshot.to_json())
        assert "snapshot_version" in data
        assert data["snapshot_version"] == SNAPSHOT_VERSION


class TestSnapshotJSONRoundTrip:
    """Snapshot serializes to JSON and deserializes back to an equal object."""

    def test_to_json_produces_string(self, sample_snapshot: Snapshot) -> None:
        result = sample_snapshot.to_json()
        assert isinstance(result, str)

    def test_json_is_valid(self, sample_snapshot: Snapshot) -> None:
        json.loads(sample_snapshot.to_json())  # must not raise

    def test_from_json_round_trip(self, sample_snapshot: Snapshot) -> None:
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert restored == sample_snapshot

    def test_round_trip_preserves_commit_sha(self, sample_snapshot: Snapshot) -> None:
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert restored.commit_sha == sample_snapshot.commit_sha

    def test_round_trip_preserves_config_hash(self, sample_snapshot: Snapshot) -> None:
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert restored.config_hash == sample_snapshot.config_hash

    def test_round_trip_preserves_language_breakdown(self, sample_snapshot: Snapshot) -> None:
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert restored.language_breakdown == sample_snapshot.language_breakdown

    def test_round_trip_preserves_divergence(self, sample_snapshot: Snapshot) -> None:
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert restored.divergence == sample_snapshot.divergence

    def test_round_trip_null_commit_sha(self, sample_divergence: DivergenceSummary) -> None:
        snap = Snapshot(
            snapshot_version=SNAPSHOT_VERSION,
            timestamp="2026-04-10T17:25:00Z",
            commit_sha=None,
            config_hash="abc",
            divergence=sample_divergence,
            file_count=0,
            language_breakdown={},
        )
        restored = Snapshot.from_json(snap.to_json())
        assert restored.commit_sha is None

    def test_round_trip_with_feature_records(
        self,
        sample_snapshot: Snapshot,
        sample_feature_record: FeatureRecord,
    ) -> None:
        sample_snapshot.feature_records.append(sample_feature_record)
        restored = Snapshot.from_json(sample_snapshot.to_json())
        assert len(restored.feature_records) == 1
        assert restored.feature_records[0] == sample_feature_record

    def test_from_dict_round_trip(self, sample_snapshot: Snapshot) -> None:
        d = sample_snapshot.to_dict()
        restored = Snapshot.from_dict(d)
        assert restored == sample_snapshot


# ---------------------------------------------------------------------------
# M16: DivergenceSummary with per-language fields
# ---------------------------------------------------------------------------


class TestDivergenceSummaryPerLanguageFields:
    """Per-language fields round-trip correctly and default to None."""

    def test_new_fields_default_to_none(self) -> None:
        d = DivergenceSummary()
        assert d.pattern_entropy_by_language is None
        assert d.pattern_entropy_by_language_delta is None
        assert d.convention_drift_by_language is None
        assert d.convention_drift_by_language_delta is None

    def test_round_trip_with_per_language_values(self) -> None:
        d = DivergenceSummary(
            pattern_entropy=3.0,
            pattern_entropy_by_language={"python": 2.0, "shell": 1.0},
            pattern_entropy_by_language_delta={"python": 1.0, "shell": 0.5},
            convention_drift_by_language={"python": 0.3, "shell": 0.1},
            convention_drift_by_language_delta={"python": 0.05, "shell": 0.0},
        )
        restored = DivergenceSummary.from_dict(d.to_dict())
        assert restored == d

    def test_from_dict_missing_per_language_keys_defaults_to_none(self) -> None:
        """Deserializing an old 0.1.0-style dict (no per-language keys) gives None."""
        old_dict = {
            "pattern_entropy": 2.0,
            "pattern_entropy_delta": None,
            "convention_drift": 0.1,
            "convention_drift_delta": None,
            "coupling_topology": 0.2,
            "coupling_topology_delta": None,
            "boundary_violations": 0,
            "boundary_violations_delta": None,
        }
        restored = DivergenceSummary.from_dict(old_dict)
        assert restored.pattern_entropy_by_language is None
        assert restored.pattern_entropy_by_language_delta is None
        assert restored.convention_drift_by_language is None
        assert restored.convention_drift_by_language_delta is None
        assert restored.pattern_entropy == 2.0

    def test_snapshot_from_dict_with_old_0_1_0_json(self) -> None:
        """Snapshot.from_dict handles a snapshot lacking per-language fields gracefully."""
        old_data = {
            "snapshot_version": "0.1.0",
            "timestamp": "2026-01-01T00:00:00Z",
            "commit_sha": None,
            "config_hash": "abc",
            "divergence": {
                "pattern_entropy": 1.0,
                "pattern_entropy_delta": None,
                "convention_drift": 0.0,
                "convention_drift_delta": None,
                "coupling_topology": 0.0,
                "coupling_topology_delta": None,
                "boundary_violations": 0,
                "boundary_violations_delta": None,
            },
            "file_count": 1,
            "language_breakdown": {"python": 1},
        }
        snap = Snapshot.from_dict(old_data)
        assert snap.divergence.pattern_entropy_by_language is None
        assert snap.divergence.convention_drift_by_language is None
        assert snap.snapshot_version == "0.1.0"
