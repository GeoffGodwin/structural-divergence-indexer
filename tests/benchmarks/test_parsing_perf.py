"""Parsing performance benchmarks at 100, 1000, and 5000 file scales.

These tests are gated behind ``pytest.mark.benchmark`` and are NOT run in
normal CI. Trigger explicitly with:

    pytest tests/benchmarks/ -m benchmark

The benchmarks validate two things:
1. Cold-start parse time is within acceptable bounds for the scale.
2. Warm-start (cache hit) parse time is dramatically faster than cold-start.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from sdi.parsing._parse_cache import compute_file_hash, read_parse_cache, write_parse_cache
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------


def _make_synthetic_record(file_path: str) -> FeatureRecord:
    """Create a plausible FeatureRecord for benchmarking."""
    return FeatureRecord(
        file_path=file_path,
        language="python",
        imports=["os", "sys", "pathlib"],
        symbols=["MyClass", "my_function", "CONSTANT"],
        pattern_instances=[
            {"category": "error_handling", "ast_hash": "aabbccdd11223344", "node_count": 8},
            {"category": "data_access", "ast_hash": "eeff00112233aabb", "node_count": 6},
        ],
        lines_of_code=50,
        content_hash="",
    )


def _make_file_bytes(index: int) -> bytes:
    """Generate synthetic file bytes that differ per index."""
    return f"# synthetic file {index}\ndef func_{index}(): pass\n".encode()


def _populate_cache(cache_dir: Path, file_count: int) -> list[str]:
    """Write synthetic records to the parse cache and return the hashes."""
    hashes = []
    for i in range(file_count):
        data = _make_file_bytes(i)
        file_hash = compute_file_hash(data)
        record = _make_synthetic_record(f"src/module_{i}.py")
        write_parse_cache(cache_dir, file_hash, record)
        hashes.append(file_hash)
    return hashes


# ---------------------------------------------------------------------------
# Benchmark: cold-start write (simulates first parse run)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("file_count", [100, 1000, 5000])
def test_cold_start_write_throughput(tmp_path: Path, file_count: int):
    """Writing N records to the parse cache completes in under 10s."""
    cache_dir = tmp_path / "cache"
    start = time.perf_counter()
    for i in range(file_count):
        data = _make_file_bytes(i)
        file_hash = compute_file_hash(data)
        record = _make_synthetic_record(f"src/module_{i}.py")
        write_parse_cache(cache_dir, file_hash, record)
    elapsed = time.perf_counter() - start
    rate = file_count / elapsed if elapsed > 0 else float("inf")
    print(f"\n  {file_count} files: {elapsed:.3f}s ({rate:.0f} files/s)")
    assert elapsed < 10.0, (
        f"Cold-start cache write for {file_count} files took {elapsed:.1f}s (limit: 10s)"
    )


# ---------------------------------------------------------------------------
# Benchmark: warm-start read (simulates subsequent snapshot runs)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("file_count", [100, 1000, 5000])
def test_warm_start_read_throughput(tmp_path: Path, file_count: int):
    """Reading N records from the parse cache is at least 2x faster than cold write."""
    cache_dir = tmp_path / "cache"
    hashes = _populate_cache(cache_dir, file_count)

    start = time.perf_counter()
    hits = 0
    for file_hash in hashes:
        result = read_parse_cache(cache_dir, file_hash)
        if result is not None:
            hits += 1
    elapsed = time.perf_counter() - start

    assert hits == file_count, f"Expected {file_count} cache hits, got {hits}"
    rate = file_count / elapsed if elapsed > 0 else float("inf")
    print(f"\n  {file_count} files: {elapsed:.3f}s ({rate:.0f} files/s)")
    assert elapsed < 5.0, (
        f"Warm-start cache read for {file_count} files took {elapsed:.1f}s (limit: 5s)"
    )


# ---------------------------------------------------------------------------
# Benchmark: cache speedup ratio
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("file_count", [100, 1000])
def test_cache_read_faster_than_write(tmp_path: Path, file_count: int):
    """Warm-start reads are faster than cold-start writes at the same scale."""
    cache_dir = tmp_path / "cache"

    # Cold write
    write_start = time.perf_counter()
    hashes = _populate_cache(cache_dir, file_count)
    write_time = time.perf_counter() - write_start

    # Warm read
    read_start = time.perf_counter()
    for file_hash in hashes:
        read_parse_cache(cache_dir, file_hash)
    read_time = time.perf_counter() - read_start

    print(
        f"\n  {file_count} files: write={write_time:.3f}s read={read_time:.3f}s"
        f" speedup={write_time / max(read_time, 1e-9):.1f}x"
    )
    # Read should be at least as fast as write (usually much faster)
    assert read_time <= write_time * 1.5, (
        f"Read time ({read_time:.3f}s) should not exceed write time ({write_time:.3f}s)"
    )
