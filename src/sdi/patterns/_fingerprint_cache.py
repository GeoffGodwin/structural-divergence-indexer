"""Fingerprint cache: content-addressed storage of per-file PatternFingerprints.

Cache files are stored at {cache_dir}/fingerprints/{hash}.json.
Keys are SHA-256 of file bytes (same hash used by the parse cache).
This avoids re-running fingerprint_from_instance on pattern_instances
for files whose content has not changed.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sdi.snapshot.model import FeatureRecord

from sdi.patterns.fingerprint import PatternFingerprint, fingerprint_from_instance

logger = logging.getLogger(__name__)

_SUBDIR = "fingerprints"


def read_fingerprint_cache(cache_dir: Path, file_hash: str) -> list[dict[str, Any]] | None:
    """Read cached fingerprint dicts for a file by content hash.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        file_hash: SHA-256 hex digest of the file bytes.

    Returns:
        List of fingerprint dicts (keys: category, structural_hash, node_count),
        or None if not cached or corrupt.
    """
    path = cache_dir / _SUBDIR / f"{file_hash}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_bytes())
        if not isinstance(data, list):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        logger.debug("Fingerprint cache entry %s is corrupt; ignoring.", path)
        return None


def write_fingerprint_cache(cache_dir: Path, file_hash: str, fps: list[PatternFingerprint]) -> None:
    """Atomically write fingerprints to the fingerprint cache.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        file_hash: SHA-256 hex digest used as the cache key.
        fps: List of PatternFingerprint objects to serialize.
    """
    subdir = cache_dir / _SUBDIR
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / f"{file_hash}.json"
    payload = [
        {"category": fp.category, "structural_hash": fp.structural_hash, "node_count": fp.node_count} for fp in fps
    ]
    tmp_fd, tmp_name = tempfile.mkstemp(dir=subdir, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(payload, fh)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def cleanup_orphan_fingerprint_cache(cache_dir: Path, active_hashes: set[str]) -> int:
    """Remove fingerprint cache entries not present in active_hashes.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        active_hashes: SHA-256 hex digests for all files in the current run.

    Returns:
        Number of cache entries removed.
    """
    subdir = cache_dir / _SUBDIR
    if not subdir.exists():
        return 0
    removed = 0
    for path in subdir.glob("*.json"):
        if path.stem not in active_hashes:
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def get_file_fingerprints(
    record: FeatureRecord,
    min_nodes: int,
    cache_dir: Path | None,
) -> list[PatternFingerprint]:
    """Return PatternFingerprints for a record, using cache when available.

    Checks the fingerprint cache first. On a miss, computes fingerprints from
    record.pattern_instances and writes to cache. Returns an empty list if no
    valid fingerprints are found.

    Args:
        record: Feature record whose pattern_instances to fingerprint.
        min_nodes: Minimum AST node count threshold (from config).
        cache_dir: Root cache directory, or None to skip caching.

    Returns:
        List of PatternFingerprint objects for this file.
    """
    file_hash = record.content_hash
    if cache_dir is not None and file_hash:
        cached = read_fingerprint_cache(cache_dir, file_hash)
        if cached is not None:
            return [
                PatternFingerprint(
                    category=d["category"],
                    structural_hash=d["structural_hash"],
                    node_count=d.get("node_count", 0),
                )
                for d in cached
            ]

    fps: list[PatternFingerprint] = []
    for instance in record.pattern_instances:
        fp = fingerprint_from_instance(instance, min_nodes)
        if fp is not None:
            fps.append(fp)

    if cache_dir is not None and file_hash:
        try:
            write_fingerprint_cache(cache_dir, file_hash, fps)
        except OSError:
            pass

    return fps
