"""Parse cache: content-addressed FeatureRecord storage.

Cache files are stored at {cache_dir}/parse_cache/{hash}.json.
Keys are SHA-256 of file bytes (hex string). Renamed files with
identical content hit the same cache entry — this is correct behaviour
because the FeatureRecord is entirely derived from file content.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

from sdi.snapshot.model import FeatureRecord

logger = logging.getLogger(__name__)

_SUBDIR = "parse_cache"


def compute_file_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes.

    Args:
        data: Raw file bytes.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(data).hexdigest()


def read_parse_cache(cache_dir: Path, file_hash: str) -> FeatureRecord | None:
    """Read a FeatureRecord from the parse cache by content hash.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        file_hash: SHA-256 hex digest of the file bytes.

    Returns:
        Deserialized FeatureRecord, or None if not cached or corrupt.
    """
    path = cache_dir / _SUBDIR / f"{file_hash}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_bytes())
        return FeatureRecord.from_dict(data)
    except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError):
        logger.debug("Parse cache entry %s is corrupt; ignoring.", path)
        return None


def write_parse_cache(cache_dir: Path, file_hash: str, record: FeatureRecord) -> None:
    """Atomically write a FeatureRecord to the parse cache.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        file_hash: SHA-256 hex digest used as the cache key.
        record: FeatureRecord to serialize.
    """
    subdir = cache_dir / _SUBDIR
    subdir.mkdir(parents=True, exist_ok=True)
    target = subdir / f"{file_hash}.json"
    tmp_fd, tmp_name = tempfile.mkstemp(dir=subdir, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as fh:
            json.dump(record.to_dict(), fh)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def cleanup_orphan_parse_cache(cache_dir: Path, active_hashes: set[str]) -> int:
    """Remove parse cache entries not present in active_hashes.

    An orphan entry is one whose content hash does not correspond to any
    currently-known file. This is called after every snapshot to reclaim
    space as files are deleted or modified.

    Args:
        cache_dir: Root cache directory (e.g. .sdi/cache).
        active_hashes: SHA-256 hex digests for all files processed in the
            current snapshot run.

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
