"""Atomic file writes and snapshot persistence.

write_atomic() is the shared primitive for all .sdi/ file writes.
It is reused by boundary spec writes and cache writes in later milestones.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
from pathlib import Path

from sdi.snapshot.model import Snapshot

# Matches filenames produced by write_snapshot(), e.g.:
#   snapshot_20260410T172500Z_a1b2c3.json
_SNAPSHOT_RE = re.compile(r"^snapshot_\d{8}T\d{6}Z_[0-9a-f]{6}\.json$")


def write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically using tempfile + os.replace.

    The tempfile is created in the same directory as path so that os.replace
    is guaranteed to be an atomic rename (POSIX) rather than a cross-device
    copy. Cleans up the tempfile on any failure so no partial files remain.

    Args:
        path: Destination file path. Parent directory must exist.
        content: UTF-8 text to write.

    Raises:
        Any exception from tempfile creation, file write, or os.replace.
    """
    tmp_path: Path | None = None
    try:
        fd, tmp_str = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        tmp_path = Path(tmp_str)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, path)
        tmp_path = None  # replace succeeded — no cleanup needed
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def write_snapshot(snapshot: Snapshot, snapshots_dir: Path) -> Path:
    """Persist a snapshot to disk and return the written file path.

    Filename format: ``snapshot_<timestamp>_<hex6>.json``
    where timestamp is the snapshot's ISO 8601 UTC timestamp with punctuation
    stripped (e.g. ``20260410T172500Z``).

    Args:
        snapshot: Snapshot instance to persist.
        snapshots_dir: Directory to write into. Created if absent.

    Returns:
        Path to the written snapshot file.
    """
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    clean_ts = snapshot.timestamp.replace("-", "").replace(":", "")
    filename = f"snapshot_{clean_ts}_{secrets.token_hex(3)}.json"
    path = snapshots_dir / filename
    write_atomic(path, snapshot.to_json())
    return path


def read_snapshot(path: Path) -> Snapshot:
    """Deserialize a snapshot from a JSON file on disk.

    Args:
        path: Path to a snapshot JSON file.

    Returns:
        Deserialized Snapshot instance.
    """
    return Snapshot.from_json(path.read_text(encoding="utf-8"))


def list_snapshots(snapshots_dir: Path) -> list[Path]:
    """Return snapshot file paths sorted chronologically (oldest first).

    Only files matching the snapshot filename pattern are included;
    other files in the directory are ignored.

    Args:
        snapshots_dir: Directory to scan.

    Returns:
        Sorted list of snapshot file paths (may be empty).
    """
    if not snapshots_dir.exists():
        return []
    paths = [p for p in snapshots_dir.iterdir() if p.is_file() and _SNAPSHOT_RE.match(p.name)]
    return sorted(paths, key=lambda p: p.name)


def enforce_retention(snapshots_dir: Path, limit: int) -> None:
    """Delete oldest snapshots when the count exceeds limit.

    This runs synchronously after every write_snapshot call. Retention is a
    hard guarantee — no deferred cleanup.

    Args:
        snapshots_dir: Directory containing snapshot files.
        limit: Maximum number of snapshots to retain. 0 means unlimited.
    """
    if limit == 0:
        return
    snapshots = list_snapshots(snapshots_dir)
    excess = len(snapshots) - limit
    if excess > 0:
        for path in snapshots[:excess]:
            path.unlink()
