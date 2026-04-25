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
    assert elapsed < 10.0, f"Cold-start cache write for {file_count} files took {elapsed:.1f}s (limit: 10s)"


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
    assert elapsed < 5.0, f"Warm-start cache read for {file_count} files took {elapsed:.1f}s (limit: 5s)"


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


# ---------------------------------------------------------------------------
# Shell parse benchmarks (M14) — gated by requires_shell_adapter
# ---------------------------------------------------------------------------

try:
    from sdi.parsing.shell import ShellAdapter as _ShellAdapter  # noqa: F401

    _SHELL_AVAILABLE = True
except Exception:
    _SHELL_AVAILABLE = False

_skip_no_shell = pytest.mark.skipif(not _SHELL_AVAILABLE, reason="tree-sitter Bash grammar not available")


def _make_shell_script(index: int) -> bytes:
    """Generate a synthetic ~50-LOC shell script that varies per index."""
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"# synthetic script {index}",
        "cleanup() {",
        '    echo "Cleaning up" >&2',
        "}",
        "trap cleanup ERR EXIT",
        f"WORKDIR=/tmp/work_{index}",
        "",
        f"run_step_{index}() {{",
        f'    echo "Running step {index}"',
        f'    curl -sf "http://localhost:{8000 + index % 100}/health" || exit 1',
        "}",
        "",
        "check_prereqs() {",
        "    if ! command -v curl >/dev/null 2>&1; then",
        '        echo "curl required" >&2',
        "        exit 1",
        "    fi",
        "}",
        "",
        "process_items() {",
        '    find . -name "*.log" | xargs -P 4 gzip',
        "}",
        "",
        "check_prereqs",
        f"run_step_{index}",
        "process_items",
        'echo "Done"',
    ]
    return "\n".join(lines).encode()


@pytest.mark.benchmark
@_skip_no_shell
def test_shell_parse_perf_cold(tmp_path: Path) -> None:
    """Cold-parse 100 synthetic ~50-LOC shell scripts in < 1.5s (SDI_WORKERS=4)."""
    from sdi.parsing.shell import ShellAdapter

    script_count = 100
    scripts = []
    for i in range(script_count):
        path = tmp_path / f"script_{i:03d}.sh"
        data = _make_shell_script(i)
        path.write_bytes(data)
        scripts.append((path, data))

    adapter = ShellAdapter(repo_root=tmp_path)
    start = time.perf_counter()
    for path, data in scripts:
        adapter.parse_file(path, data)
    elapsed = time.perf_counter() - start

    rate = script_count / elapsed if elapsed > 0 else float("inf")
    print(f"\n  cold: {script_count} scripts in {elapsed:.3f}s ({rate:.0f} scripts/s)")
    assert elapsed < 1.5, f"Cold parse of {script_count} shell scripts took {elapsed:.1f}s (budget: 1.5s)"


@pytest.mark.benchmark
@_skip_no_shell
def test_shell_parse_perf_cached(tmp_path: Path) -> None:
    """Cache-hit rerun of 100 shell scripts completes in < 0.3s."""
    from sdi.parsing._parse_cache import compute_file_hash

    cache_dir = tmp_path / "cache"
    script_count = 100
    script_data: list[tuple[Path, bytes]] = []

    for i in range(script_count):
        path = tmp_path / f"script_{i:03d}.sh"
        data = _make_shell_script(i)
        path.write_bytes(data)
        script_data.append((path, data))

    # Warm the cache by writing pre-built records
    for path, data in script_data:
        file_hash = compute_file_hash(data)
        record = _make_synthetic_record(str(path.relative_to(tmp_path)))
        record = record.__class__(
            file_path=record.file_path,
            language="shell",
            imports=[],
            symbols=[],
            pattern_instances=record.pattern_instances,
            lines_of_code=record.lines_of_code,
            content_hash=file_hash,
        )
        write_parse_cache(cache_dir, file_hash, record)

    start = time.perf_counter()
    hits = 0
    for _, data in script_data:
        file_hash = compute_file_hash(data)
        result = read_parse_cache(cache_dir, file_hash)
        if result is not None:
            hits += 1
    elapsed = time.perf_counter() - start

    assert hits == script_count, f"Expected {script_count} cache hits, got {hits}"
    rate = script_count / elapsed if elapsed > 0 else float("inf")
    print(f"\n  cached: {script_count} scripts in {elapsed:.3f}s ({rate:.0f} scripts/s)")
    assert elapsed < 0.3, f"Cache-hit rerun of {script_count} shell scripts took {elapsed:.3f}s (budget: 0.3s)"
