"""M16 integration tests for per-language fields in CLI output.

Tests sdi show and sdi diff output with snapshots that include
per-language entropy and drift data. Snapshots are injected directly
via write_snapshot() — no tree-sitter parsing invoked.
"""

from __future__ import annotations

import json
from pathlib import Path

from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, FeatureRecord, Snapshot
from sdi.snapshot.storage import write_snapshot
from tests.conftest import run_sdi


def _write_per_language_snapshot(snapshots_dir: Path) -> None:
    """Write a snapshot with populated per-language entropy and drift fields."""
    snap = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-12T10:00:00Z",
        commit_sha=None,
        config_hash="cafebabe01234567",
        divergence=DivergenceSummary(
            pattern_entropy=3.0,
            pattern_entropy_delta=None,
            convention_drift=0.25,
            convention_drift_delta=None,
            coupling_topology=0.1,
            coupling_topology_delta=None,
            boundary_violations=0,
            boundary_violations_delta=None,
            pattern_entropy_by_language={"python": 2.0, "shell": 1.0},
            pattern_entropy_by_language_delta=None,
            convention_drift_by_language={"python": 0.3, "shell": 0.1},
            convention_drift_by_language_delta=None,
        ),
        file_count=5,
        language_breakdown={"python": 3, "shell": 2},
    )
    write_snapshot(snap, snapshots_dir)


def _make_python_catalog_dict() -> dict:
    """Return a minimal serialized PatternCatalog with two Python-attributed shapes.

    Both shapes reference files that will be listed in the companion feature_records,
    so per_language_pattern_entropy and per_language_convention_drift will produce
    non-empty results for 'python'.
    """
    return {
        "categories": {
            "error_handling": {
                "name": "error_handling",
                "entropy": 2,
                "canonical_hash": "shape_dominant",
                "shapes": {
                    "shape_dominant": {
                        "structural_hash": "shape_dominant",
                        "instance_count": 2,
                        "file_paths": ["src/foo.py", "src/foo.py"],
                        "velocity": None,
                        "boundary_spread": None,
                    },
                    "shape_minor": {
                        "structural_hash": "shape_minor",
                        "instance_count": 1,
                        "file_paths": ["src/bar.py"],
                        "velocity": None,
                        "boundary_spread": None,
                    },
                },
            }
        }
    }


def _write_diff_pair(snapshots_dir: Path) -> None:
    """Write two snapshots for diff testing.

    snap_a is minimal (no catalog).  snap_b has feature_records and a
    pattern_catalog so that compute_delta produces non-None per-language
    entropy and drift values.  Different timestamps ensure correct sort order.
    """
    snap_a = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-11T09:00:00Z",
        commit_sha=None,
        config_hash="cafebabe01234567",
        divergence=DivergenceSummary(),
        file_count=0,
        language_breakdown={},
    )
    write_snapshot(snap_a, snapshots_dir)

    snap_b = Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp="2026-04-11T10:00:00Z",
        commit_sha=None,
        config_hash="cafebabe01234567",
        divergence=DivergenceSummary(),
        file_count=2,
        language_breakdown={"python": 2},
        feature_records=[
            FeatureRecord(
                file_path="src/foo.py",
                language="python",
                imports=[],
                symbols=[],
                pattern_instances=[],
                lines_of_code=10,
            ),
            FeatureRecord(
                file_path="src/bar.py",
                language="python",
                imports=[],
                symbols=[],
                pattern_instances=[],
                lines_of_code=5,
            ),
        ],
        pattern_catalog=_make_python_catalog_dict(),
    )
    write_snapshot(snap_b, snapshots_dir)


class TestShowPerLanguageOutput:
    """sdi show renders per-language fields correctly."""

    def test_show_json_includes_per_language_fields(self, cli_runner, sdi_project_dir):
        """JSON show output includes per-language entropy keys when the snapshot has them."""
        _write_per_language_snapshot(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["--format", "json", "show"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        div = data["divergence"]
        assert "pattern_entropy_by_language" in div
        by_lang = div["pattern_entropy_by_language"]
        assert "python" in by_lang
        assert "shell" in by_lang

    def test_show_json_includes_convention_drift_by_language(self, cli_runner, sdi_project_dir):
        """JSON show output includes convention_drift_by_language when the snapshot has it."""
        _write_per_language_snapshot(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["--format", "json", "show"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        div = data["divergence"]
        assert "convention_drift_by_language" in div
        by_lang = div["convention_drift_by_language"]
        assert by_lang is not None
        assert "python" in by_lang
        assert "shell" in by_lang

    def test_show_text_renders_per_language_section(self, cli_runner, sdi_project_dir):
        """Text-mode show renders a Per-Language Pattern Entropy section."""
        _write_per_language_snapshot(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["show"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        assert "Per-Language Pattern Entropy" in result.output
        assert "python" in result.output
        assert "shell" in result.output


class TestDiffPerLanguageOutput:
    """sdi diff renders per-language fields correctly."""

    def test_diff_text_renders_per_language_section(self, cli_runner, sdi_project_dir):
        """Text-mode diff renders a Per-Language Pattern Entropy section.

        compute_delta recomputes per-language data from snap_b's feature_records
        and pattern_catalog; the section appears only when those are populated.
        """
        _write_diff_pair(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["diff"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        assert "Per-Language Pattern Entropy" in result.output
        assert "python" in result.output

    def test_diff_json_includes_convention_drift_by_language(self, cli_runner, sdi_project_dir):
        """JSON diff output includes convention_drift_by_language and its delta.

        Verifies that the convention_drift_by_language path is exercised through
        the CLI diff code path (compute_delta → diff_cmd JSON serialization).
        """
        _write_diff_pair(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["--format", "json", "diff"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        div = data["divergence"]
        assert "convention_drift_by_language" in div
        by_lang = div["convention_drift_by_language"]
        assert by_lang is not None
        assert "python" in by_lang
        assert "convention_drift_by_language_delta" in div
        delta = div["convention_drift_by_language_delta"]
        assert delta is not None
        assert "python" in delta

    def test_diff_json_includes_pattern_entropy_by_language(self, cli_runner, sdi_project_dir):
        """JSON diff output includes pattern_entropy_by_language and its delta."""
        _write_diff_pair(sdi_project_dir / ".sdi" / "snapshots")
        result = run_sdi(cli_runner, ["--format", "json", "diff"], sdi_project_dir)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        div = data["divergence"]
        assert "pattern_entropy_by_language" in div
        by_lang = div["pattern_entropy_by_language"]
        assert by_lang is not None
        assert "python" in by_lang
        assert div["pattern_entropy_by_language_delta"] is not None
