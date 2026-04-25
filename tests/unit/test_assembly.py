"""Unit tests for sdi.snapshot.assembly — assemble_snapshot() and _compute_config_hash()."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdi.config import (
    BoundariesConfig,
    CoreConfig,
    OutputConfig,
    PatternsConfig,
    SDIConfig,
    SnapshotsConfig,
)
from sdi.detection.leiden import CommunityResult
from sdi.patterns.catalog import CategoryStats, PatternCatalog, ShapeStats
from sdi.snapshot.assembly import _attach_intent_divergence, _compute_config_hash, assemble_snapshot
from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, FeatureRecord, Snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    *,
    languages: str = "auto",
    exclude: list[str] | None = None,
    random_seed: int = 42,
    leiden_gamma: float = 1.0,
    stability_threshold: int = 3,
    weighted_edges: bool = False,
    categories: str = "auto",
    min_pattern_nodes: int = 5,
    snapshots_dir: str = ".sdi/snapshots",
    retention: int = 100,
    output_format: str = "text",
    output_color: str = "auto",
) -> SDIConfig:
    """Construct an SDIConfig with explicit analysis and non-analysis settings."""
    return SDIConfig(
        core=CoreConfig(
            languages=languages,
            exclude=exclude or ["**/vendor/**"],
            random_seed=random_seed,
        ),
        snapshots=SnapshotsConfig(dir=snapshots_dir, retention=retention),
        boundaries=BoundariesConfig(
            leiden_gamma=leiden_gamma,
            stability_threshold=stability_threshold,
            weighted_edges=weighted_edges,
        ),
        patterns=PatternsConfig(
            categories=categories,
            min_pattern_nodes=min_pattern_nodes,
        ),
        output=OutputConfig(format=output_format, color=output_color),
    )


def _make_catalog(shapes_by_category: dict[str, list[str]] | None = None) -> PatternCatalog:
    """Build a minimal PatternCatalog with given hashes per category."""
    shapes_by_category = shapes_by_category or {}
    categories: dict[str, CategoryStats] = {}
    for cat_name, hashes in shapes_by_category.items():
        shapes = {
            h: ShapeStats(
                structural_hash=h,
                instance_count=1,
                file_paths=["src/a.py"],
                velocity=None,
                boundary_spread=None,
            )
            for h in hashes
        }
        categories[cat_name] = CategoryStats(name=cat_name, shapes=shapes)
    return PatternCatalog(categories=categories)


def _make_records(languages: list[str] | None = None) -> list[FeatureRecord]:
    """Build a list of minimal FeatureRecords."""
    languages = languages or ["python", "python", "typescript"]
    return [
        FeatureRecord(
            file_path=f"src/file_{i}.{lang[:2]}",
            language=lang,
            imports=[],
            symbols=[],
            pattern_instances=[],
            lines_of_code=10,
        )
        for i, lang in enumerate(languages)
    ]


def _make_community() -> CommunityResult:
    return CommunityResult(
        partition=[0, 1],
        stability_score=1.0,
        cluster_count=2,
        inter_cluster_edges=[{"source_cluster": 0, "target_cluster": 1, "count": 2}],
        surface_area_ratios={0: 0.5, 1: 0.5},
        vertex_names=["src/a.py", "src/b.py"],
    )


def _make_graph_metrics(density: float = 0.1) -> dict:
    return {
        "node_count": 10,
        "edge_count": 5,
        "density": density,
        "cycle_count": 0,
        "hub_concentration": 0.0,
        "component_count": 1,
        "max_depth": 2,
        "hub_nodes": [],
    }


def _make_prior_snapshot() -> Snapshot:
    """Build a minimal prior snapshot for delta computation."""
    return Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-09T00:00:00Z",
        commit_sha=None,
        config_hash="abcd1234",
        divergence=DivergenceSummary(
            pattern_entropy=1.0,
            pattern_entropy_delta=None,
            convention_drift=0.0,
            convention_drift_delta=None,
            coupling_topology=0.1,
            coupling_topology_delta=None,
            boundary_violations=1,
            boundary_violations_delta=None,
        ),
        file_count=5,
        language_breakdown={"python": 5},
        graph_metrics=_make_graph_metrics(density=0.05),
        pattern_catalog=_make_catalog({"error_handling": ["h1"]}).to_dict(),
        partition_data={
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [{"source_cluster": 0, "target_cluster": 1, "count": 1}],
            "cluster_count": 2,
            "stability_score": 1.0,
        },
    )


# ---------------------------------------------------------------------------
# _compute_config_hash: 16-char hex, deterministic, sensitive to analysis keys
# ---------------------------------------------------------------------------


class TestComputeConfigHash:
    """_compute_config_hash() must return a deterministic 16-char hex digest."""

    def test_returns_16_char_string(self) -> None:
        cfg = _make_config()
        result = _compute_config_hash(cfg)
        assert isinstance(result, str)
        assert len(result) == 16

    def test_returns_hex_string(self) -> None:
        cfg = _make_config()
        result = _compute_config_hash(cfg)
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_same_config(self) -> None:
        cfg = _make_config()
        assert _compute_config_hash(cfg) == _compute_config_hash(cfg)

    def test_deterministic_two_identical_configs(self) -> None:
        cfg_a = _make_config(random_seed=99)
        cfg_b = _make_config(random_seed=99)
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)

    # Analysis-affecting fields — must change the hash

    def test_sensitive_to_core_languages(self) -> None:
        cfg_a = _make_config(languages="auto")
        cfg_b = _make_config(languages="python")
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_core_random_seed(self) -> None:
        cfg_a = _make_config(random_seed=42)
        cfg_b = _make_config(random_seed=99)
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_core_exclude(self) -> None:
        cfg_a = _make_config(exclude=["**/vendor/**"])
        cfg_b = _make_config(exclude=["**/node_modules/**"])
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_exclude_order_independent(self) -> None:
        """Exclude list is sorted before hashing, so order must not matter."""
        cfg_a = _make_config(exclude=["**/vendor/**", "**/node_modules/**"])
        cfg_b = _make_config(exclude=["**/node_modules/**", "**/vendor/**"])
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)

    def test_sensitive_to_leiden_gamma(self) -> None:
        cfg_a = _make_config(leiden_gamma=1.0)
        cfg_b = _make_config(leiden_gamma=2.0)
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_stability_threshold(self) -> None:
        cfg_a = _make_config(stability_threshold=3)
        cfg_b = _make_config(stability_threshold=5)
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_weighted_edges(self) -> None:
        cfg_a = _make_config(weighted_edges=False)
        cfg_b = _make_config(weighted_edges=True)
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_pattern_categories(self) -> None:
        cfg_a = _make_config(categories="auto")
        cfg_b = _make_config(categories="error_handling")
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    def test_sensitive_to_min_pattern_nodes(self) -> None:
        cfg_a = _make_config(min_pattern_nodes=5)
        cfg_b = _make_config(min_pattern_nodes=10)
        assert _compute_config_hash(cfg_a) != _compute_config_hash(cfg_b)

    # Non-analysis fields — must NOT change the hash

    def test_insensitive_to_output_format(self) -> None:
        cfg_a = _make_config(output_format="text")
        cfg_b = _make_config(output_format="json")
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)

    def test_insensitive_to_output_color(self) -> None:
        cfg_a = _make_config(output_color="auto")
        cfg_b = _make_config(output_color="never")
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)

    def test_insensitive_to_snapshots_retention(self) -> None:
        cfg_a = _make_config(retention=100)
        cfg_b = _make_config(retention=10)
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)

    def test_insensitive_to_snapshots_dir(self) -> None:
        cfg_a = _make_config(snapshots_dir=".sdi/snapshots")
        cfg_b = _make_config(snapshots_dir="/tmp/alt-snapshots")
        assert _compute_config_hash(cfg_a) == _compute_config_hash(cfg_b)


# ---------------------------------------------------------------------------
# assemble_snapshot: chain correctness with mocked storage layer
# ---------------------------------------------------------------------------

_STORAGE_MODULE = "sdi.snapshot.assembly"


class TestAssembleSnapshotFirstSnapshot:
    """When no prior snapshot exists, deltas are None and the chain runs correctly."""

    def test_returns_snapshot_instance(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha="abc123",
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert isinstance(result, Snapshot)

    def test_all_delta_fields_are_none_on_first_snapshot(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.divergence.pattern_entropy_delta is None
        assert result.divergence.convention_drift_delta is None
        assert result.divergence.coupling_topology_delta is None
        assert result.divergence.boundary_violations_delta is None

    def test_write_snapshot_called_once(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot") as mock_write,
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        mock_write.assert_called_once()

    def test_enforce_retention_called_after_write(self, tmp_path: Path) -> None:
        """Retention must be enforced synchronously after every write."""
        cfg = _make_config(retention=5)
        call_order: list[str] = []
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(
                f"{_STORAGE_MODULE}.write_snapshot",
                side_effect=lambda *a, **kw: call_order.append("write"),
            ),
            patch(
                f"{_STORAGE_MODULE}.enforce_retention",
                side_effect=lambda *a, **kw: call_order.append("retain"),
            ),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert call_order == ["write", "retain"], "enforce_retention must be called immediately after write_snapshot"

    def test_enforce_retention_receives_correct_limit(self, tmp_path: Path) -> None:
        cfg = _make_config(retention=7)
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention") as mock_retain,
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        _, kwargs = mock_retain.call_args
        args = mock_retain.call_args[0]
        limit_arg = args[1] if len(args) > 1 else kwargs.get("limit")
        assert limit_arg == 7


class TestAssembleSnapshotFileMetadata:
    """Returned Snapshot must carry correct file counts and language breakdown."""

    def test_file_count_equals_record_count(self, tmp_path: Path) -> None:
        cfg = _make_config()
        records = _make_records(["python", "python", "typescript", "go"])
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=records,
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.file_count == 4

    def test_language_breakdown_counts_correctly(self, tmp_path: Path) -> None:
        cfg = _make_config()
        records = _make_records(["python", "python", "typescript"])
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=records,
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.language_breakdown == {"python": 2, "typescript": 1}

    def test_empty_records_gives_empty_breakdown(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=[],
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.file_count == 0
        assert result.language_breakdown == {}

    def test_snapshot_version_is_current(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha="abc",
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.snapshot_version == SNAPSHOT_VERSION

    def test_config_hash_is_set(self, tmp_path: Path) -> None:
        cfg = _make_config()
        expected_hash = _compute_config_hash(cfg)
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.config_hash == expected_hash

    def test_commit_sha_preserved(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha="deadbeef",
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.commit_sha == "deadbeef"

    def test_none_commit_sha_preserved(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.commit_sha is None


class TestAssembleSnapshotWithPrevious:
    """When a prior snapshot exists, deltas are computed against it."""

    def test_deltas_are_not_none_when_previous_exists(self, tmp_path: Path) -> None:
        cfg = _make_config()
        prior = _make_prior_snapshot()
        fake_path = tmp_path / "snapshot_20260409T000000Z_aabbcc.json"

        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[fake_path]),
            patch(f"{_STORAGE_MODULE}.read_snapshot", return_value=prior),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(density=0.2),
                community=_make_community(),
                catalog=_make_catalog({"error_handling": ["h1", "h2"]}),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )

        assert result.divergence.pattern_entropy_delta is not None
        assert result.divergence.convention_drift_delta is not None
        assert result.divergence.coupling_topology_delta is not None
        assert result.divergence.boundary_violations_delta is not None

    def test_read_snapshot_called_with_most_recent_path(self, tmp_path: Path) -> None:
        """The most recent path (last in sorted list) is passed to read_snapshot."""
        cfg = _make_config()
        prior = _make_prior_snapshot()
        old_path = tmp_path / "snapshot_20260401T000000Z_aa0000.json"
        new_path = tmp_path / "snapshot_20260409T000000Z_bb0000.json"

        with (
            patch(
                f"{_STORAGE_MODULE}.list_snapshots",
                return_value=[old_path, new_path],
            ),
            patch(f"{_STORAGE_MODULE}.read_snapshot", return_value=prior) as mock_read,
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )

        mock_read.assert_called_once_with(new_path)

    def test_write_snapshot_receives_assembled_snapshot(self, tmp_path: Path) -> None:
        """write_snapshot must receive the final assembled Snapshot object."""
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot") as mock_write,
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )

        written_snap = mock_write.call_args[0][0]
        assert isinstance(written_snap, Snapshot)
        assert written_snap is result


class TestAssembleSnapshotCommunityData:
    """Partition data from CommunityResult is stored in the snapshot."""

    def test_partition_data_populated_when_community_provided(self, tmp_path: Path) -> None:
        cfg = _make_config()
        community = _make_community()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=community,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.partition_data != {}
        assert result.partition_data["cluster_count"] == 2
        assert result.partition_data["vertex_names"] == ["src/a.py", "src/b.py"]

    def test_partition_data_empty_when_community_is_none(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
        ):
            result = assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path,
            )
        assert result.partition_data == {}


class TestAssembleSnapshotPathValidation:
    """snapshots_dir that resolves outside repo_root must raise SystemExit(2)."""

    def test_raises_systemexit_for_traversal_path(self, tmp_path: Path) -> None:
        """snapshots.dir with path traversal must be rejected."""
        cfg = _make_config(snapshots_dir="../../etc/evil")
        with pytest.raises(SystemExit):
            assemble_snapshot(
                records=[],
                graph_metrics={},
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path / "repo",
            )

    def test_systemexit_code_is_2_for_traversal(self, tmp_path: Path) -> None:
        cfg = _make_config(snapshots_dir="../../etc/evil")
        with pytest.raises(SystemExit) as exc_info:
            assemble_snapshot(
                records=[],
                graph_metrics={},
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-10T12:00:00Z",
                repo_root=tmp_path / "repo",
            )
        # SystemExit(2, msg) stores code as tuple (2, msg)
        code = exc_info.value.code
        exit_code = code[0] if isinstance(code, tuple) else code
        assert exit_code == 2


class TestAssembleSnapshotRealDiskRoundTrip:
    """End-to-end: assemble writes a readable snapshot file to disk."""

    def test_snapshot_file_created_on_disk(self, tmp_path: Path) -> None:
        cfg = _make_config(snapshots_dir=".sdi/snapshots")
        assemble_snapshot(
            records=_make_records(["python", "python"]),
            graph_metrics=_make_graph_metrics(),
            community=_make_community(),
            catalog=_make_catalog({"error_handling": ["h1"]}),
            config=cfg,
            commit_sha="abc123",
            timestamp="2026-04-10T12:00:00Z",
            repo_root=tmp_path,
        )
        snapshots_dir = tmp_path / ".sdi" / "snapshots"
        written_files = list(snapshots_dir.glob("snapshot_*.json"))
        assert len(written_files) == 1

    def test_written_snapshot_is_readable(self, tmp_path: Path) -> None:
        from sdi.snapshot.storage import list_snapshots, read_snapshot

        cfg = _make_config(snapshots_dir=".sdi/snapshots")
        result = assemble_snapshot(
            records=_make_records(["python"]),
            graph_metrics=_make_graph_metrics(),
            community=None,
            catalog=_make_catalog(),
            config=cfg,
            commit_sha=None,
            timestamp="2026-04-10T12:00:00Z",
            repo_root=tmp_path,
        )
        snapshots_dir = tmp_path / ".sdi" / "snapshots"
        paths = list_snapshots(snapshots_dir)
        assert len(paths) == 1
        read_back = read_snapshot(paths[0])
        assert read_back.snapshot_version == result.snapshot_version
        assert read_back.timestamp == result.timestamp
        assert read_back.file_count == result.file_count

    def test_retention_enforced_on_disk(self, tmp_path: Path) -> None:
        """With retention=2, after 3 writes only 2 files remain."""
        cfg = _make_config(snapshots_dir=".sdi/snapshots", retention=2)
        timestamps = [
            "2026-04-10T10:00:00Z",
            "2026-04-10T11:00:00Z",
            "2026-04-10T12:00:00Z",
        ]
        for ts in timestamps:
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp=ts,
                repo_root=tmp_path,
            )
        snapshots_dir = tmp_path / ".sdi" / "snapshots"
        written_files = list(snapshots_dir.glob("snapshot_*.json"))
        assert len(written_files) == 2

    def test_second_snapshot_has_non_none_deltas(self, tmp_path: Path) -> None:
        """Two real snapshots must produce non-null deltas on the second."""
        cfg = _make_config(snapshots_dir=".sdi/snapshots")
        assemble_snapshot(
            records=_make_records(["python"]),
            graph_metrics=_make_graph_metrics(density=0.1),
            community=None,
            catalog=_make_catalog({"eh": ["h1"]}),
            config=cfg,
            commit_sha=None,
            timestamp="2026-04-10T10:00:00Z",
            repo_root=tmp_path,
        )
        second = assemble_snapshot(
            records=_make_records(["python", "python"]),
            graph_metrics=_make_graph_metrics(density=0.3),
            community=_make_community(),
            catalog=_make_catalog({"eh": ["h1", "h2"]}),
            config=cfg,
            commit_sha=None,
            timestamp="2026-04-10T11:00:00Z",
            repo_root=tmp_path,
        )
        assert second.divergence.pattern_entropy_delta is not None
        assert second.divergence.boundary_violations_delta is not None


# ---------------------------------------------------------------------------
# _attach_intent_divergence: M9 addition — attaches intent_divergence to partition_data
# ---------------------------------------------------------------------------


_MINIMAL_BOUNDARIES_YAML = """\
sdi_boundaries:
  version: "0.1.0"
  modules:
    - name: billing
      paths: ["src/billing/"]
"""


def _config_with_spec(spec_file: str) -> SDIConfig:
    """Build an SDIConfig with the given boundaries spec_file path."""
    cfg = _make_config()
    cfg.boundaries = BoundariesConfig(spec_file=spec_file)
    return cfg


class TestAttachIntentDivergence:
    """_attach_intent_divergence() attaches or skips intent_divergence on partition_data."""

    def test_does_nothing_on_empty_partition_dict(self, tmp_path: Path) -> None:
        """Empty part_dict is returned unchanged — no key inserted."""
        cfg = _config_with_spec("boundaries.yaml")
        part_dict: dict = {}
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        assert part_dict == {}

    def test_does_nothing_when_no_spec_file(self, tmp_path: Path) -> None:
        """Absent boundaries.yaml → intent_divergence key is not added."""
        cfg = _config_with_spec("nonexistent_boundaries.yaml")
        part_dict = {
            "partition": [0, 1],
            "vertex_names": ["src/a.py", "src/b.py"],
            "inter_cluster_edges": [],
            "cluster_count": 2,
            "stability_score": 1.0,
        }
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        assert "intent_divergence" not in part_dict

    def test_attaches_intent_divergence_when_spec_exists(self, tmp_path: Path) -> None:
        """When boundaries.yaml exists, intent_divergence is inserted into part_dict."""
        spec_path = tmp_path / "boundaries.yaml"
        spec_path.write_text(_MINIMAL_BOUNDARIES_YAML, encoding="utf-8")

        cfg = _config_with_spec("boundaries.yaml")
        part_dict = {
            "partition": [0, 1],
            "vertex_names": ["src/billing/a.py", "src/other/b.py"],
            "inter_cluster_edges": [],
            "cluster_count": 2,
            "stability_score": 1.0,
        }
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        assert "intent_divergence" in part_dict

    def test_intent_divergence_key_has_expected_structure(self, tmp_path: Path) -> None:
        """intent_divergence dict must contain total_violations and list fields."""
        spec_path = tmp_path / "boundaries.yaml"
        spec_path.write_text(_MINIMAL_BOUNDARIES_YAML, encoding="utf-8")

        cfg = _config_with_spec("boundaries.yaml")
        part_dict = {
            "partition": [0],
            "vertex_names": ["src/billing/a.py"],
            "inter_cluster_edges": [],
            "cluster_count": 1,
            "stability_score": 1.0,
        }
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        intent_div = part_dict["intent_divergence"]
        assert "total_violations" in intent_div
        assert "misplaced_files" in intent_div
        assert "unauthorized_cross_boundary" in intent_div
        assert "layer_violations" in intent_div

    def test_misplaced_file_detected_via_assembly(self, tmp_path: Path) -> None:
        """A file in billing/ but in a different cluster is reflected in total_violations > 0."""
        spec_path = tmp_path / "boundaries.yaml"
        spec_path.write_text(_MINIMAL_BOUNDARIES_YAML, encoding="utf-8")

        cfg = _config_with_spec("boundaries.yaml")
        # billing/a.py and billing/b.py are in different clusters → one is misplaced
        part_dict = {
            "partition": [0, 1],
            "vertex_names": ["src/billing/a.py", "src/billing/b.py"],
            "inter_cluster_edges": [],
            "cluster_count": 2,
            "stability_score": 1.0,
        }
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        assert part_dict["intent_divergence"]["total_violations"] > 0

    def test_no_violations_when_partition_matches_spec(self, tmp_path: Path) -> None:
        """All billing files in one cluster → zero misplaced files, zero total_violations."""
        spec_path = tmp_path / "boundaries.yaml"
        spec_path.write_text(_MINIMAL_BOUNDARIES_YAML, encoding="utf-8")

        cfg = _config_with_spec("boundaries.yaml")
        part_dict = {
            "partition": [0, 0, 0],
            "vertex_names": ["src/billing/a.py", "src/billing/b.py", "src/billing/c.py"],
            "inter_cluster_edges": [],
            "cluster_count": 1,
            "stability_score": 1.0,
        }
        _attach_intent_divergence(part_dict, cfg, tmp_path)
        assert part_dict["intent_divergence"]["total_violations"] == 0


# ---------------------------------------------------------------------------
# _cleanup_caches integration: orphan cleanup called after write + retention
# ---------------------------------------------------------------------------

_CLEANUP_PARSE = "sdi.snapshot.assembly.cleanup_orphan_parse_cache"
_CLEANUP_FP = "sdi.snapshot.assembly.cleanup_orphan_fingerprint_cache"


def _make_records_with_hashes(hashes: list[str]) -> list[FeatureRecord]:
    """Build FeatureRecords with specified content_hash values."""
    return [
        FeatureRecord(
            file_path=f"src/file_{i}.py",
            language="python",
            imports=[],
            symbols=[],
            pattern_instances=[],
            lines_of_code=5,
            content_hash=h,
        )
        for i, h in enumerate(hashes)
    ]


class TestAssembleSnapshotCleanupCaches:
    """assemble_snapshot must invoke orphan cache cleanup after write and retention."""

    def test_cleanup_parse_cache_called(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE) as mock_parse_cleanup,
            patch(_CLEANUP_FP),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        mock_parse_cleanup.assert_called_once()

    def test_cleanup_fingerprint_cache_called(self, tmp_path: Path) -> None:
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE),
            patch(_CLEANUP_FP) as mock_fp_cleanup,
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        mock_fp_cleanup.assert_called_once()

    def test_cleanup_receives_repo_root_cache_dir(self, tmp_path: Path) -> None:
        """Cleanup must be called with repo_root/.sdi/cache as the cache_dir."""
        cfg = _make_config()
        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE) as mock_parse_cleanup,
            patch(_CLEANUP_FP),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        called_cache_dir = mock_parse_cleanup.call_args[0][0]
        assert called_cache_dir == tmp_path / ".sdi" / "cache"

    def test_active_hashes_derived_from_record_content_hashes(self, tmp_path: Path) -> None:
        """active_hashes passed to cleanup must equal the set of non-empty content_hashes."""
        cfg = _make_config()
        hash_a = "a" * 64
        hash_b = "b" * 64
        records = _make_records_with_hashes([hash_a, hash_b])

        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE) as mock_parse_cleanup,
            patch(_CLEANUP_FP),
        ):
            assemble_snapshot(
                records=records,
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        called_active_hashes = mock_parse_cleanup.call_args[0][1]
        assert called_active_hashes == {hash_a, hash_b}

    def test_empty_content_hash_excluded_from_active_hashes(self, tmp_path: Path) -> None:
        """Records with empty content_hash must NOT be included in active_hashes."""
        cfg = _make_config()
        hash_a = "c" * 64
        records = _make_records_with_hashes([hash_a, ""])  # second record has no hash

        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE) as mock_parse_cleanup,
            patch(_CLEANUP_FP),
        ):
            assemble_snapshot(
                records=records,
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        called_active_hashes = mock_parse_cleanup.call_args[0][1]
        assert "" not in called_active_hashes
        assert hash_a in called_active_hashes
        assert len(called_active_hashes) == 1

    def test_all_empty_content_hashes_gives_empty_active_set(self, tmp_path: Path) -> None:
        """When all records have empty content_hash, active_hashes is an empty set."""
        cfg = _make_config()
        records = _make_records_with_hashes(["", "", ""])

        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(f"{_STORAGE_MODULE}.write_snapshot"),
            patch(f"{_STORAGE_MODULE}.enforce_retention"),
            patch(_CLEANUP_PARSE) as mock_parse_cleanup,
            patch(_CLEANUP_FP),
        ):
            assemble_snapshot(
                records=records,
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        called_active_hashes = mock_parse_cleanup.call_args[0][1]
        assert called_active_hashes == set()

    def test_cleanup_called_after_write_and_retention(self, tmp_path: Path) -> None:
        """Cleanup must happen after write_snapshot and enforce_retention."""
        cfg = _make_config()
        call_order: list[str] = []

        with (
            patch(f"{_STORAGE_MODULE}.list_snapshots", return_value=[]),
            patch(
                f"{_STORAGE_MODULE}.write_snapshot",
                side_effect=lambda *a, **kw: call_order.append("write"),
            ),
            patch(
                f"{_STORAGE_MODULE}.enforce_retention",
                side_effect=lambda *a, **kw: call_order.append("retain"),
            ),
            patch(
                _CLEANUP_PARSE,
                side_effect=lambda *a, **kw: call_order.append("cleanup_parse"),
            ),
            patch(
                _CLEANUP_FP,
                side_effect=lambda *a, **kw: call_order.append("cleanup_fp"),
            ),
        ):
            assemble_snapshot(
                records=_make_records(["python"]),
                graph_metrics=_make_graph_metrics(),
                community=None,
                catalog=_make_catalog(),
                config=cfg,
                commit_sha=None,
                timestamp="2026-04-24T12:00:00Z",
                repo_root=tmp_path,
            )
        assert call_order.index("write") < call_order.index("retain")
        assert call_order.index("retain") < call_order.index("cleanup_parse")
        assert call_order.index("retain") < call_order.index("cleanup_fp")
