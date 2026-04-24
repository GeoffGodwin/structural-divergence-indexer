"""Unit tests for sdi.parsing._parse_cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdi.parsing._parse_cache import (
    cleanup_orphan_parse_cache,
    compute_file_hash,
    read_parse_cache,
    write_parse_cache,
)
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(file_path: str = "src/foo.py", content_hash: str = "") -> FeatureRecord:
    return FeatureRecord(
        file_path=file_path,
        language="python",
        imports=["os"],
        symbols=["Foo"],
        pattern_instances=[],
        lines_of_code=10,
        content_hash=content_hash,
    )


# ---------------------------------------------------------------------------
# compute_file_hash
# ---------------------------------------------------------------------------


def test_compute_file_hash_returns_64_char_hex():
    h = compute_file_hash(b"hello world")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_file_hash_deterministic():
    data = b"def foo(): pass\n"
    assert compute_file_hash(data) == compute_file_hash(data)


def test_compute_file_hash_different_content_different_hash():
    h1 = compute_file_hash(b"foo")
    h2 = compute_file_hash(b"bar")
    assert h1 != h2


def test_compute_file_hash_same_content_renamed_file_same_hash():
    content = b"class MyClass: pass\n"
    assert compute_file_hash(content) == compute_file_hash(content)


# ---------------------------------------------------------------------------
# read_parse_cache — cache miss
# ---------------------------------------------------------------------------


def test_read_parse_cache_miss_nonexistent_dir(tmp_path: Path):
    result = read_parse_cache(tmp_path / "cache", "abc123")
    assert result is None


def test_read_parse_cache_miss_hash_not_found(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "parse_cache").mkdir()
    result = read_parse_cache(cache_dir, "deadbeef" * 8)
    assert result is None


# ---------------------------------------------------------------------------
# write_parse_cache + read_parse_cache — cache hit
# ---------------------------------------------------------------------------


def test_write_then_read_returns_same_record(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = _make_record()
    file_hash = compute_file_hash(b"hello")
    write_parse_cache(cache_dir, file_hash, record)
    result = read_parse_cache(cache_dir, file_hash)
    assert result is not None
    assert result.file_path == record.file_path
    assert result.language == record.language
    assert result.imports == record.imports


def test_cache_hit_preserves_all_fields(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = FeatureRecord(
        file_path="src/complex.py",
        language="python",
        imports=["os", "sys"],
        symbols=["Alpha", "Beta"],
        pattern_instances=[{"category": "error_handling", "ast_hash": "abc123", "node_count": 7}],
        lines_of_code=42,
        content_hash="",
    )
    file_hash = compute_file_hash(b"complex content")
    write_parse_cache(cache_dir, file_hash, record)
    result = read_parse_cache(cache_dir, file_hash)
    assert result is not None
    assert result.symbols == ["Alpha", "Beta"]
    assert result.lines_of_code == 42
    assert len(result.pattern_instances) == 1


def test_cache_file_created_atomically(tmp_path: Path):
    """Cache file appears at expected path after write."""
    cache_dir = tmp_path / "cache"
    record = _make_record()
    file_hash = "a" * 64
    write_parse_cache(cache_dir, file_hash, record)
    expected = cache_dir / "parse_cache" / f"{file_hash}.json"
    assert expected.exists()


# ---------------------------------------------------------------------------
# Cache invalidation — changed file = different hash = cache miss
# ---------------------------------------------------------------------------


def test_changed_file_invalidates_cache(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record_v1 = _make_record(file_path="src/foo.py")
    hash_v1 = compute_file_hash(b"version 1")
    hash_v2 = compute_file_hash(b"version 2 - different")
    write_parse_cache(cache_dir, hash_v1, record_v1)

    # v1 hash: hit; v2 hash: miss
    assert read_parse_cache(cache_dir, hash_v1) is not None
    assert read_parse_cache(cache_dir, hash_v2) is None


# ---------------------------------------------------------------------------
# Corrupt cache file — treated as miss, not an error
# ---------------------------------------------------------------------------


def test_corrupt_cache_file_returns_none(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    subdir = cache_dir / "parse_cache"
    subdir.mkdir(parents=True)
    file_hash = "b" * 64
    (subdir / f"{file_hash}.json").write_text("NOT VALID JSON{{{{")
    result = read_parse_cache(cache_dir, file_hash)
    assert result is None


def test_truncated_cache_file_returns_none(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    subdir = cache_dir / "parse_cache"
    subdir.mkdir(parents=True)
    file_hash = "c" * 64
    (subdir / f"{file_hash}.json").write_text('{"file_path": "x"}')
    result = read_parse_cache(cache_dir, file_hash)
    assert result is None


# ---------------------------------------------------------------------------
# cleanup_orphan_parse_cache
# ---------------------------------------------------------------------------


def test_orphan_cleanup_removes_stale_entries(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = _make_record()

    hash_active = compute_file_hash(b"active file")
    hash_stale = compute_file_hash(b"old deleted file")

    write_parse_cache(cache_dir, hash_active, record)
    write_parse_cache(cache_dir, hash_stale, record)

    active_hashes = {hash_active}
    removed = cleanup_orphan_parse_cache(cache_dir, active_hashes)

    assert removed == 1
    assert read_parse_cache(cache_dir, hash_active) is not None
    assert read_parse_cache(cache_dir, hash_stale) is None


def test_orphan_cleanup_preserves_all_when_all_active(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = _make_record()

    hashes = {compute_file_hash(f"file {i}".encode()) for i in range(3)}
    for h in hashes:
        write_parse_cache(cache_dir, h, record)

    removed = cleanup_orphan_parse_cache(cache_dir, hashes)
    assert removed == 0


def test_orphan_cleanup_noop_missing_dir(tmp_path: Path):
    removed = cleanup_orphan_parse_cache(tmp_path / "cache", set())
    assert removed == 0


def test_orphan_cleanup_removes_all_when_active_empty(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = _make_record()
    hashes = [compute_file_hash(f"file {i}".encode()) for i in range(2)]
    for h in hashes:
        write_parse_cache(cache_dir, h, record)

    removed = cleanup_orphan_parse_cache(cache_dir, set())
    assert removed == 2


# ---------------------------------------------------------------------------
# content_hash is propagated on cache hit
# ---------------------------------------------------------------------------


def test_cached_record_gets_content_hash_populated(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    record = _make_record()
    file_hash = compute_file_hash(b"my source")
    write_parse_cache(cache_dir, file_hash, record)

    cached = read_parse_cache(cache_dir, file_hash)
    assert cached is not None
    cached.content_hash = file_hash
    assert cached.content_hash == file_hash
