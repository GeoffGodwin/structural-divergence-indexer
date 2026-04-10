"""Tests for sdi.snapshot.storage — atomic writes, listing, retention."""

from __future__ import annotations

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
    """Create a minimal Snapshot with the given timestamp."""
    return Snapshot(
        snapshot_version=SNAPSHOT_VERSION,
        timestamp=timestamp,
        commit_sha=None,
        config_hash="abc123",
        divergence=DivergenceSummary(),
        file_count=0,
        language_breakdown={},
    )


class TestWriteAtomic:
    def test_creates_file_with_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        write_atomic(target, "hello world")
        assert target.exists()
        assert target.read_text() == "hello world"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        target.write_text("old content")
        write_atomic(target, "new content")
        assert target.read_text() == "new content"

    def test_crash_safety_target_absent_after_failure(self, tmp_path: Path) -> None:
        """When os.replace raises, the target must not exist."""
        target = tmp_path / "output.txt"
        with patch("os.replace", side_effect=OSError("simulated crash")):
            with pytest.raises(OSError):
                write_atomic(target, "content")
        assert not target.exists()

    def test_crash_safety_no_temp_files_remain(self, tmp_path: Path) -> None:
        """When os.replace raises, no .tmp files should remain in the directory."""
        target = tmp_path / "output.txt"
        with patch("os.replace", side_effect=OSError("simulated crash")):
            with pytest.raises(OSError):
                write_atomic(target, "content")
        remaining = list(tmp_path.iterdir())
        assert remaining == [], f"Unexpected files: {remaining}"

    def test_unicode_content(self, tmp_path: Path) -> None:
        target = tmp_path / "unicode.txt"
        content = "Hello, 世界! 🎉"
        write_atomic(target, content)
        assert target.read_text(encoding="utf-8") == content


class TestListSnapshots:
    def test_empty_directory(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        snapshots_dir.mkdir()
        assert list_snapshots(snapshots_dir) == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        assert list_snapshots(tmp_path / "does_not_exist") == []

    def test_sorted_chronologically(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        # Write out-of-order to confirm sort is by name, not insertion order
        snaps = [
            _make_snapshot("2026-04-10T17:30:00Z"),
            _make_snapshot("2026-04-10T17:25:00Z"),
            _make_snapshot("2026-04-10T17:35:00Z"),
        ]
        for s in snaps:
            write_snapshot(s, snapshots_dir)
        listed = list_snapshots(snapshots_dir)
        assert len(listed) == 3
        names = [p.name for p in listed]
        assert names == sorted(names), "Snapshots must be listed in chronological (alphabetical) order"

    def test_ignores_non_snapshot_files(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        snapshots_dir.mkdir()
        (snapshots_dir / "README.md").write_text("# hi")
        (snapshots_dir / "not_a_snapshot.json").write_text("{}")
        (snapshots_dir / "snapshot_bad.json").write_text("{}")
        assert list_snapshots(snapshots_dir) == []

    def test_returns_path_objects(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        write_snapshot(_make_snapshot("2026-04-10T17:00:00Z"), snapshots_dir)
        result = list_snapshots(snapshots_dir)
        assert len(result) == 1
        assert isinstance(result[0], Path)


class TestWriteAndReadSnapshot:
    def test_roundtrip(self, tmp_path: Path) -> None:
        snap = _make_snapshot("2026-04-10T17:00:00Z")
        snap.file_count = 42
        snap.language_breakdown = {"python": 42}
        snapshots_dir = tmp_path / "snapshots"
        path = write_snapshot(snap, snapshots_dir)
        recovered = read_snapshot(path)
        assert recovered.file_count == 42
        assert recovered.language_breakdown == {"python": 42}
        assert recovered.snapshot_version == SNAPSHOT_VERSION

    def test_creates_snapshots_dir_if_absent(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "new_dir" / "snapshots"
        assert not snapshots_dir.exists()
        write_snapshot(_make_snapshot("2026-04-10T17:00:00Z"), snapshots_dir)
        assert snapshots_dir.exists()


class TestEnforceRetention:
    def test_within_limit_no_deletion(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        for i in range(3):
            write_snapshot(_make_snapshot(f"2026-04-10T17:2{i}:00Z"), snapshots_dir)
        enforce_retention(snapshots_dir, limit=5)
        assert len(list_snapshots(snapshots_dir)) == 3

    def test_deletes_oldest_when_exceeded(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        timestamps = [
            "2026-04-10T17:21:00Z",  # oldest — should be deleted
            "2026-04-10T17:22:00Z",  # should be deleted
            "2026-04-10T17:23:00Z",
            "2026-04-10T17:24:00Z",
            "2026-04-10T17:25:00Z",  # newest — must survive
        ]
        for ts in timestamps:
            write_snapshot(_make_snapshot(ts), snapshots_dir)
        enforce_retention(snapshots_dir, limit=3)
        remaining = list_snapshots(snapshots_dir)
        assert len(remaining) == 3
        names = [p.name for p in remaining]
        assert not any("T172100Z" in n for n in names), "Oldest snapshot should be deleted"
        assert not any("T172200Z" in n for n in names), "Second oldest should be deleted"
        assert any("T172500Z" in n for n in names), "Newest snapshot must survive"

    def test_unlimited_retention(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        for i in range(10):
            write_snapshot(_make_snapshot(f"2026-04-10T17:{i:02d}:00Z"), snapshots_dir)
        enforce_retention(snapshots_dir, limit=0)
        assert len(list_snapshots(snapshots_dir)) == 10

    def test_exactly_at_limit_no_deletion(self, tmp_path: Path) -> None:
        snapshots_dir = tmp_path / "snapshots"
        for i in range(3):
            write_snapshot(_make_snapshot(f"2026-04-10T17:2{i}:00Z"), snapshots_dir)
        enforce_retention(snapshots_dir, limit=3)
        assert len(list_snapshots(snapshots_dir)) == 3
