"""Tests for sdi.snapshot.model — Snapshot, DivergenceSummary, FeatureRecord."""

from __future__ import annotations

import json

import pytest

from sdi.snapshot.model import (
    SNAPSHOT_VERSION,
    DivergenceSummary,
    FeatureRecord,
    Snapshot,
)


class TestFeatureRecord:
    def test_construction(self, sample_feature_record: FeatureRecord) -> None:
        fr = sample_feature_record
        assert fr.file_path == "src/foo.py"
        assert fr.language == "python"
        assert fr.imports == ["os", "pathlib"]
        assert fr.symbols == ["MyClass", "my_function"]
        assert fr.lines_of_code == 50

    def test_to_dict_contains_all_fields(self, sample_feature_record: FeatureRecord) -> None:
        d = sample_feature_record.to_dict()
        assert d["file_path"] == "src/foo.py"
        assert d["language"] == "python"
        assert d["imports"] == ["os", "pathlib"]
        assert d["symbols"] == ["MyClass", "my_function"]
        assert d["lines_of_code"] == 50

    def test_from_dict_roundtrip(self, sample_feature_record: FeatureRecord) -> None:
        d = sample_feature_record.to_dict()
        fr2 = FeatureRecord.from_dict(d)
        assert fr2 == sample_feature_record

    def test_pattern_instances_preserved(self) -> None:
        fr = FeatureRecord(
            file_path="x.py",
            language="python",
            imports=[],
            symbols=[],
            pattern_instances=[{"type": "class_def", "name": "Foo", "size": 5}],
            lines_of_code=10,
        )
        d = fr.to_dict()
        assert d["pattern_instances"] == [{"type": "class_def", "name": "Foo", "size": 5}]
        fr2 = FeatureRecord.from_dict(d)
        assert fr2.pattern_instances == fr.pattern_instances


class TestDivergenceSummary:
    def test_all_none_on_first_snapshot(self) -> None:
        div = DivergenceSummary()
        assert div.pattern_entropy is None
        assert div.pattern_entropy_delta is None
        assert div.convention_drift is None
        assert div.convention_drift_delta is None
        assert div.coupling_topology is None
        assert div.coupling_topology_delta is None
        assert div.boundary_violations is None
        assert div.boundary_violations_delta is None

    def test_with_values(self, sample_divergence: DivergenceSummary) -> None:
        assert sample_divergence.pattern_entropy == 1.5
        assert sample_divergence.boundary_violations == 2
        # Deltas are None on first snapshot — zero ≠ None
        assert sample_divergence.pattern_entropy_delta is None

    def test_roundtrip(self, sample_divergence: DivergenceSummary) -> None:
        d = sample_divergence.to_dict()
        div2 = DivergenceSummary.from_dict(d)
        assert div2 == sample_divergence

    def test_none_values_serialized_as_null(self) -> None:
        div = DivergenceSummary(pattern_entropy=1.0)
        d = div.to_dict()
        assert d["pattern_entropy"] == 1.0
        assert d["pattern_entropy_delta"] is None


class TestSnapshot:
    def test_snapshot_version_present(self, sample_snapshot: Snapshot) -> None:
        assert sample_snapshot.snapshot_version == SNAPSHOT_VERSION
        assert sample_snapshot.snapshot_version != ""

    def test_json_roundtrip(self, sample_snapshot: Snapshot) -> None:
        json_str = sample_snapshot.to_json()
        snap2 = Snapshot.from_json(json_str)
        assert snap2.snapshot_version == sample_snapshot.snapshot_version
        assert snap2.timestamp == sample_snapshot.timestamp
        assert snap2.commit_sha == sample_snapshot.commit_sha
        assert snap2.config_hash == sample_snapshot.config_hash
        assert snap2.file_count == sample_snapshot.file_count
        assert snap2.language_breakdown == sample_snapshot.language_breakdown
        assert snap2.divergence == sample_snapshot.divergence

    def test_json_contains_snapshot_version(self, sample_snapshot: Snapshot) -> None:
        data = json.loads(sample_snapshot.to_json())
        assert "snapshot_version" in data
        assert data["snapshot_version"] == SNAPSHOT_VERSION

    def test_null_commit_sha_roundtrips(self) -> None:
        snap = Snapshot(
            snapshot_version=SNAPSHOT_VERSION,
            timestamp="2026-04-10T17:25:00Z",
            commit_sha=None,
            config_hash="abc",
            divergence=DivergenceSummary(),
            file_count=0,
            language_breakdown={},
        )
        snap2 = Snapshot.from_json(snap.to_json())
        assert snap2.commit_sha is None

    def test_to_dict_has_required_fields(self, sample_snapshot: Snapshot) -> None:
        d = sample_snapshot.to_dict()
        for key in ("snapshot_version", "timestamp", "commit_sha", "config_hash",
                    "divergence", "file_count", "language_breakdown"):
            assert key in d, f"Missing field: {key}"

    def test_feature_records_roundtrip(self, sample_snapshot: Snapshot, sample_feature_record: FeatureRecord) -> None:
        sample_snapshot.feature_records = [sample_feature_record]
        snap2 = Snapshot.from_json(sample_snapshot.to_json())
        assert len(snap2.feature_records) == 1
        assert snap2.feature_records[0] == sample_feature_record

    def test_empty_feature_records_by_default(self, sample_snapshot: Snapshot) -> None:
        assert sample_snapshot.feature_records == []
