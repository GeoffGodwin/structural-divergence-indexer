"""Unit tests for sdi.patterns._fingerprint_cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdi.patterns._fingerprint_cache import (
    cleanup_orphan_fingerprint_cache,
    get_file_fingerprints,
    read_fingerprint_cache,
    write_fingerprint_cache,
)
from sdi.patterns.fingerprint import PatternFingerprint
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fp(
    category: str = "error_handling",
    structural_hash: str = "aabbccdd11223344",
    node_count: int = 7,
) -> PatternFingerprint:
    return PatternFingerprint(
        category=category,
        structural_hash=structural_hash,
        node_count=node_count,
    )


def _make_record(
    content_hash: str = "a" * 64,
    pattern_instances: list | None = None,
) -> FeatureRecord:
    if pattern_instances is None:
        pattern_instances = []
    return FeatureRecord(
        file_path="src/foo.py",
        language="python",
        imports=["os"],
        symbols=["Foo"],
        pattern_instances=pattern_instances,
        lines_of_code=10,
        content_hash=content_hash,
    )


_SUBDIR = "fingerprints"


# ---------------------------------------------------------------------------
# read_fingerprint_cache — cache miss paths
# ---------------------------------------------------------------------------


def test_read_miss_nonexistent_dir(tmp_path: Path) -> None:
    result = read_fingerprint_cache(tmp_path / "cache", "deadbeef" * 8)
    assert result is None


def test_read_miss_hash_not_found(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    (cache_dir / _SUBDIR).mkdir(parents=True)
    result = read_fingerprint_cache(cache_dir, "b" * 64)
    assert result is None


def test_read_corrupt_json_returns_none(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    subdir = cache_dir / _SUBDIR
    subdir.mkdir(parents=True)
    file_hash = "c" * 64
    (subdir / f"{file_hash}.json").write_text("NOT VALID JSON{{{{")
    assert read_fingerprint_cache(cache_dir, file_hash) is None


def test_read_non_list_json_returns_none(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    subdir = cache_dir / _SUBDIR
    subdir.mkdir(parents=True)
    file_hash = "d" * 64
    (subdir / f"{file_hash}.json").write_text(json.dumps({"not": "a list"}))
    assert read_fingerprint_cache(cache_dir, file_hash) is None


# ---------------------------------------------------------------------------
# write_fingerprint_cache + read_fingerprint_cache — roundtrip
# ---------------------------------------------------------------------------


def test_write_then_read_roundtrip_preserves_all_fields(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "e" * 64
    fps = [
        _make_fp(category="error_handling", structural_hash="1122334455667788", node_count=9),
        _make_fp(category="data_access", structural_hash="aabbccddeeff0011", node_count=3),
    ]
    write_fingerprint_cache(cache_dir, file_hash, fps)
    result = read_fingerprint_cache(cache_dir, file_hash)

    assert result is not None
    assert len(result) == 2
    assert result[0]["category"] == "error_handling"
    assert result[0]["structural_hash"] == "1122334455667788"
    assert result[0]["node_count"] == 9
    assert result[1]["category"] == "data_access"


def test_write_creates_file_at_expected_path(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "f" * 64
    write_fingerprint_cache(cache_dir, file_hash, [_make_fp()])
    expected = cache_dir / _SUBDIR / f"{file_hash}.json"
    assert expected.exists()


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    cache_dir = tmp_path / "deeply" / "nested" / "cache"
    assert not cache_dir.exists()
    write_fingerprint_cache(cache_dir, "a" * 64, [_make_fp()])
    assert (cache_dir / _SUBDIR / f"{'a' * 64}.json").exists()


def test_write_empty_fps_list_is_valid(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "0" * 64
    write_fingerprint_cache(cache_dir, file_hash, [])
    result = read_fingerprint_cache(cache_dir, file_hash)
    assert result == []


def test_write_then_read_produces_valid_json_file(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "1" * 64
    fps = [_make_fp(structural_hash="deadbeefcafe0001")]
    write_fingerprint_cache(cache_dir, file_hash, fps)
    raw = json.loads((cache_dir / _SUBDIR / f"{file_hash}.json").read_bytes())
    assert isinstance(raw, list)
    assert raw[0]["structural_hash"] == "deadbeefcafe0001"


# ---------------------------------------------------------------------------
# cleanup_orphan_fingerprint_cache
# ---------------------------------------------------------------------------


def test_cleanup_removes_stale_preserves_active(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    active_hash = "a" * 64
    stale_hash = "b" * 64
    write_fingerprint_cache(cache_dir, active_hash, [_make_fp()])
    write_fingerprint_cache(cache_dir, stale_hash, [_make_fp()])

    removed = cleanup_orphan_fingerprint_cache(cache_dir, {active_hash})

    assert removed == 1
    assert read_fingerprint_cache(cache_dir, active_hash) is not None
    assert read_fingerprint_cache(cache_dir, stale_hash) is None


def test_cleanup_preserves_all_when_all_active(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    hashes = {f"{i}" * 64 for i in range(3)}
    for h in hashes:
        write_fingerprint_cache(cache_dir, h, [_make_fp()])

    removed = cleanup_orphan_fingerprint_cache(cache_dir, hashes)
    assert removed == 0


def test_cleanup_noop_on_missing_dir(tmp_path: Path) -> None:
    removed = cleanup_orphan_fingerprint_cache(tmp_path / "cache", set())
    assert removed == 0


def test_cleanup_removes_all_when_active_set_empty(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    hashes = ["c" * 64, "d" * 64]
    for h in hashes:
        write_fingerprint_cache(cache_dir, h, [_make_fp()])

    removed = cleanup_orphan_fingerprint_cache(cache_dir, set())
    assert removed == 2
    for h in hashes:
        assert read_fingerprint_cache(cache_dir, h) is None


def test_cleanup_returns_count_of_removed_entries(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    all_hashes = [f"{i}" * 64 for i in range(5)]
    active = {all_hashes[0], all_hashes[1]}
    for h in all_hashes:
        write_fingerprint_cache(cache_dir, h, [_make_fp()])

    removed = cleanup_orphan_fingerprint_cache(cache_dir, active)
    assert removed == 3


# ---------------------------------------------------------------------------
# get_file_fingerprints — cache_dir=None (caching disabled)
# ---------------------------------------------------------------------------


def test_get_file_fingerprints_no_cache_dir_returns_fps(tmp_path: Path) -> None:
    instances = [{"category": "error_handling", "ast_hash": "hash0011aabbccdd", "node_count": 8}]
    record = _make_record(content_hash="a" * 64, pattern_instances=instances)

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=None)

    assert len(fps) == 1
    assert fps[0].category == "error_handling"
    assert fps[0].structural_hash == "hash0011aabbccdd"


def test_get_file_fingerprints_no_cache_dir_does_not_write_files(tmp_path: Path) -> None:
    instances = [{"category": "error_handling", "ast_hash": "hash0011aabbccdd", "node_count": 8}]
    record = _make_record(content_hash="a" * 64, pattern_instances=instances)

    get_file_fingerprints(record, min_nodes=1, cache_dir=None)

    assert not (tmp_path / "fingerprints").exists()


# ---------------------------------------------------------------------------
# get_file_fingerprints — cache miss: computes and writes to cache
# ---------------------------------------------------------------------------


def test_get_file_fingerprints_cache_miss_computes_fps(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    instances = [{"category": "error_handling", "ast_hash": "computed1122aabb", "node_count": 6}]
    record = _make_record(content_hash="e" * 64, pattern_instances=instances)

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    assert len(fps) == 1
    assert fps[0].structural_hash == "computed1122aabb"
    assert fps[0].category == "error_handling"


def test_get_file_fingerprints_cache_miss_writes_to_cache(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "f" * 64
    instances = [{"category": "data_access", "ast_hash": "writtenhash001122", "node_count": 5}]
    record = _make_record(content_hash=file_hash, pattern_instances=instances)

    get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    cached = read_fingerprint_cache(cache_dir, file_hash)
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["structural_hash"] == "writtenhash001122"


def test_get_file_fingerprints_min_nodes_filters_small_instances(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    instances = [
        {"category": "error_handling", "ast_hash": "big_hash_0011aabb", "node_count": 10},
        {"category": "error_handling", "ast_hash": "small_hash_ccddee", "node_count": 2},
    ]
    record = _make_record(content_hash="4" * 64, pattern_instances=instances)

    fps = get_file_fingerprints(record, min_nodes=5, cache_dir=cache_dir)

    assert len(fps) == 1
    assert fps[0].structural_hash == "big_hash_0011aabb"


def test_get_file_fingerprints_empty_instances_returns_empty_list(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    record = _make_record(content_hash="5" * 64, pattern_instances=[])

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    assert fps == []


# ---------------------------------------------------------------------------
# get_file_fingerprints — cache hit: returns cached fps without recomputing
# ---------------------------------------------------------------------------


def test_get_file_fingerprints_cache_hit_returns_cached_data(tmp_path: Path) -> None:
    """Cache-hit path must return the persisted fingerprints, not recompute from instances."""
    cache_dir = tmp_path / "cache"
    file_hash = "7" * 64

    # Write a known fingerprint into the cache under this hash
    cached_fp = _make_fp(category="error_handling", structural_hash="cached_sentinel_1122", node_count=7)
    write_fingerprint_cache(cache_dir, file_hash, [cached_fp])

    # Create a record with the same content_hash but different pattern_instances
    # (would produce a different structural_hash if computed fresh)
    different_instances = [{"category": "data_access", "ast_hash": "computed_different_99", "node_count": 8}]
    record = _make_record(content_hash=file_hash, pattern_instances=different_instances)

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    assert len(fps) == 1
    # If it used the cache, structural_hash is "cached_sentinel_1122"
    # If it recomputed, structural_hash would be "computed_different_99"
    assert fps[0].structural_hash == "cached_sentinel_1122"
    assert fps[0].category == "error_handling"


def test_get_file_fingerprints_cache_hit_returns_pattern_fingerprint_objects(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    file_hash = "8" * 64
    write_fingerprint_cache(cache_dir, file_hash, [_make_fp(node_count=12)])
    record = _make_record(content_hash=file_hash)

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    assert all(isinstance(fp, PatternFingerprint) for fp in fps)
    assert fps[0].node_count == 12


# ---------------------------------------------------------------------------
# get_file_fingerprints — empty content_hash with non-None cache_dir
# ---------------------------------------------------------------------------


def test_get_file_fingerprints_empty_hash_falls_through_to_compute(tmp_path: Path) -> None:
    """An empty content_hash must skip the cache and compute directly from instances."""
    cache_dir = tmp_path / "cache"
    instances = [{"category": "error_handling", "ast_hash": "direct_computed_ab", "node_count": 6}]
    record = _make_record(content_hash="", pattern_instances=instances)

    fps = get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    assert len(fps) == 1
    assert fps[0].structural_hash == "direct_computed_ab"


def test_get_file_fingerprints_empty_hash_does_not_write_cache(tmp_path: Path) -> None:
    """Empty content_hash must not create any cache files."""
    cache_dir = tmp_path / "cache"
    instances = [{"category": "error_handling", "ast_hash": "some_hash_aabbcc", "node_count": 6}]
    record = _make_record(content_hash="", pattern_instances=instances)

    get_file_fingerprints(record, min_nodes=1, cache_dir=cache_dir)

    subdir = cache_dir / _SUBDIR
    assert not subdir.exists() or list(subdir.glob("*.json")) == []
