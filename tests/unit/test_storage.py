"""Unit tests for sdi.snapshot.storage — atomic writes, listing, retention."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from sdi.snapshot.model import SNAPSHOT_VERSION, DivergenceSummary, Snapshot
from sdi.snapshot.storage import (
    enforce_retention,
    list_snapshots,
    read_snapshot,
    write_atomic,
    write_snapshot,
)


def _make_snapshot(timestamp: str) -> Snapshot:
    """Helper: build a minimal Snapshot with a given timestamp."""
    return Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp=timestamp,
        commit_sha=None,
        config_hash="test",
        divergence=DivergenceSummary(),
        file_count=0,
        language_breakdown={},
    )


class TestWriteAtomic:
    """write_atomic creates the file via tempfile + os.replace."""

    def test_creates_file(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        write_atomic(target, "hello")
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "hello"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "out.txt"
        target.write_text("old", encoding="utf-8")
        write_atomic(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_no_partial_file_on_failure(self, tmp_path: Path) -> None:
        """A simulated write failure must leave no .tmp artifact."""
        target = tmp_path / "out.txt"

        with patch("os.replace", side_effect=OSError("simulated failure")):
            with pytest.raises(OSError):
                write_atomic(target, "content")

        # The target file must not have been created
        assert not target.exists()
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_uses_same_directory_for_tempfile(self, tmp_path: Path) -> None:
        """Tempfile must be created in the same dir as target (atomic POSIX rename)."""
        target = tmp_path / "out.txt"
        created_temp_dirs: list[str] = []

        original_mkstemp = __import__("tempfile").mkstemp

        def recording_mkstemp(**kwargs: object) -> tuple:
            created_temp_dirs.append(str(kwargs.get("dir", "")))
            return original_mkstemp(**kwargs)

        with patch("tempfile.mkstemp", side_effect=recording_mkstemp):
            write_atomic(target, "x")

        assert any(str(tmp_path) in d for d in created_temp_dirs)


class TestWriteSnapshot:
    """write_snapshot persists a Snapshot and returns its path."""

    def test_creates_file(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        path = write_snapshot(snap, tmp_path)
        assert path.exists()

    def test_filename_contains_timestamp(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        path = write_snapshot(snap, tmp_path)
        assert "20260410T172500Z" in path.name

    def test_filename_matches_pattern(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T00:00:00Z")
        path = write_snapshot(snap, tmp_path)
        import re
        assert re.match(r"^snapshot_\d{8}T\d{6}Z_[0-9a-f]{6}\.json$", path.name)

    def test_written_file_is_valid_json(self, tmp_path: Path) -> None:
        import json
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        path = write_snapshot(snap, tmp_path)
        json.loads(path.read_text(encoding="utf-8"))  # must not raise

    def test_round_trip_read_write(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        path = write_snapshot(snap, tmp_path)
        restored = read_snapshot(path)
        assert restored == snap

    def test_creates_dir_if_absent(self, tmp_path: Path) -> None:
        snaps_dir = tmp_path / "new_dir" / "snapshots"
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        write_snapshot(snap, snaps_dir)
        assert snaps_dir.exists()


class TestListSnapshots:
    """list_snapshots returns snapshot files sorted oldest first."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert list_snapshots(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        assert list_snapshots(tmp_path / "nope") == []

    def test_sorted_chronologically(self, tmp_path: Path) -> None:
        snaps = [
            _make_snapshot("2026-04-10T17:25:00Z"),
            _make_snapshot("2026-04-09T12:00:00Z"),
            _make_snapshot("2026-04-11T08:30:00Z"),
        ]
        for s in snaps:
            write_snapshot(s, tmp_path)
        paths = list_snapshots(tmp_path)
        names = [p.name for p in paths]
        assert names == sorted(names)

    def test_ignores_non_snapshot_files(self, tmp_path: Path) -> None:
        (tmp_path / "README.txt").write_text("not a snapshot", encoding="utf-8")
        (tmp_path / "snapshot_bad.json").write_text("{}", encoding="utf-8")
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        write_snapshot(snap, tmp_path)
        paths = list_snapshots(tmp_path)
        assert len(paths) == 1

    def test_returns_only_matching_filenames(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T17:25:00Z")
        write_snapshot(snap, tmp_path)
        paths = list_snapshots(tmp_path)
        for p in paths:
            assert p.suffix == ".json"
            assert p.name.startswith("snapshot_")


class TestEnforceRetention:
    """enforce_retention deletes oldest snapshots above the limit."""

    def test_no_deletion_under_limit(self, tmp_path: Path) -> None:
        for i in range(3):
            write_snapshot(_make_snapshot(f"2026-04-0{i + 1}T00:00:00Z"), tmp_path)
        enforce_retention(tmp_path, limit=5)
        assert len(list_snapshots(tmp_path)) == 3

    def test_deletes_oldest_when_exceeded(self, tmp_path: Path) -> None:
        timestamps = [
            "2026-04-01T00:00:00Z",
            "2026-04-02T00:00:00Z",
            "2026-04-03T00:00:00Z",
        ]
        for ts in timestamps:
            write_snapshot(_make_snapshot(ts), tmp_path)
        enforce_retention(tmp_path, limit=2)
        remaining = list_snapshots(tmp_path)
        assert len(remaining) == 2
        # The oldest (2026-04-01) should have been deleted
        assert "20260401T000000Z" not in remaining[0].name

    def test_zero_limit_means_unlimited(self, tmp_path: Path) -> None:
        for i in range(10):
            write_snapshot(_make_snapshot(f"2026-04-{i + 1:02d}T00:00:00Z"), tmp_path)
        enforce_retention(tmp_path, limit=0)
        assert len(list_snapshots(tmp_path)) == 10

    def test_exact_limit_no_deletion(self, tmp_path: Path) -> None:
        for i in range(5):
            write_snapshot(_make_snapshot(f"2026-04-0{i + 1}T00:00:00Z"), tmp_path)
        enforce_retention(tmp_path, limit=5)
        assert len(list_snapshots(tmp_path)) == 5
