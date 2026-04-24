# Coder Summary
## Status: COMPLETE

## What Was Implemented

Milestone 10: Caching and Performance Optimization

1. **`src/sdi/parsing/_parse_cache.py`** (NEW) — Content-addressed parse cache keyed by SHA-256 of file bytes. Stores FeatureRecords at `.sdi/cache/parse_cache/<hash>.json` using atomic writes (tempfile + `os.replace`). Public API: `compute_file_hash`, `read_parse_cache`, `write_parse_cache`, `cleanup_orphan_parse_cache`.

2. **`src/sdi/patterns/_fingerprint_cache.py`** (NEW) — Content-addressed fingerprint cache keyed by SHA-256 of file bytes. Stores PatternFingerprint lists at `.sdi/cache/fingerprints/<hash>.json` using atomic writes. Public API: `read_fingerprint_cache`, `write_fingerprint_cache`, `cleanup_orphan_fingerprint_cache`, `get_file_fingerprints` (check/compute/write helper used by catalog builder).

3. **`src/sdi/parsing/_runner.py`** (MODIFIED) — `_parse_one` now computes the SHA-256 hash of file bytes before tree-sitter parsing, checks the parse cache first, and writes to the cache on a miss. Always sets `record.content_hash`. Args tuple extended from 3-tuple to 4-tuple to include `cache_dir_str`. Cache dir is fixed at `{repo_root}/.sdi/cache`.

4. **`src/sdi/snapshot/model.py`** (MODIFIED) — Added `content_hash: str = ""` field to `FeatureRecord`. Old snapshots deserialize with `content_hash=""` (backward compatible via `data.get("content_hash", "")`). This field carries the SHA-256 hash through the pipeline so assembly can run orphan cleanup without re-reading files.

5. **`src/sdi/patterns/catalog.py`** (MODIFIED) — `build_pattern_catalog` now accepts `cache_dir: Path | None = None`. Inner loop replaced: `fingerprint_from_instance` calls are now delegated to `get_file_fingerprints` from `_fingerprint_cache.py`, which handles cache check/compute/write. Import of `fingerprint_from_instance` removed (now internal to `_fingerprint_cache.py`).

6. **`src/sdi/snapshot/assembly.py`** (MODIFIED) — `assemble_snapshot` calls `_cleanup_caches()` after writing the snapshot and enforcing retention. `_cleanup_caches` removes orphan parse and fingerprint cache entries whose hash is not in the active set (`{r.content_hash for r in records if r.content_hash}`).

7. **`src/sdi/cli/snapshot_cmd.py`** (MODIFIED) — Passes `cache_dir = repo_root / ".sdi" / "cache"` to `build_pattern_catalog`.

8. **`tests/unit/test_parse_cache.py`** (NEW) — 17 unit tests: `compute_file_hash` correctness and determinism; cache miss on nonexistent dir or hash; write then read roundtrip preserving all fields; atomic write verification; changed file invalidates cache; corrupt/truncated cache returns None; orphan cleanup removes stale / preserves active / noop on missing dir / removes all when empty.

9. **`tests/benchmarks/__init__.py`** (NEW) — Package init for benchmarks directory.

10. **`tests/benchmarks/test_parsing_perf.py`** (NEW) — 9 benchmark tests (all gated behind `pytest.mark.benchmark`) measuring cold-start write throughput and warm-start read throughput at 100/1000/5000 file scales, plus cache read vs write speed comparison.

11. **`tests/benchmarks/test_leiden_perf.py`** (NEW) — 6 benchmark tests (all gated behind `pytest.mark.benchmark`) measuring Leiden partition time at 100/1000/5000/10000 node scales, and warm-start vs cold-start comparison. Auto-skipped if igraph/leidenalg are absent.

12. **`pyproject.toml`** (MODIFIED) — Added `benchmark` marker registration to `[tool.pytest.ini_options]` so benchmarks can be excluded with `-m "not benchmark"`.

## Root Cause (bugs only)
N/A — Milestone 10 feature implementation.

## Files Modified
- `src/sdi/parsing/_parse_cache.py` — (NEW) Parse cache: compute_file_hash, read/write/cleanup
- `src/sdi/parsing/_runner.py` — Integrated parse cache into _parse_one and parse_repository
- `src/sdi/patterns/_fingerprint_cache.py` — (NEW) Fingerprint cache: read/write/cleanup + get_file_fingerprints helper
- `src/sdi/patterns/catalog.py` — Use fingerprint cache in build_pattern_catalog; added cache_dir param
- `src/sdi/snapshot/model.py` — Added content_hash field to FeatureRecord
- `src/sdi/snapshot/assembly.py` — Added orphan cache cleanup after snapshot write
- `src/sdi/cli/snapshot_cmd.py` — Pass cache_dir to build_pattern_catalog
- `pyproject.toml` — Added benchmark pytest marker
- `tests/unit/test_parse_cache.py` — (NEW) 17 unit tests for parse cache
- `tests/benchmarks/__init__.py` — (NEW) Package init
- `tests/benchmarks/test_parsing_perf.py` — (NEW) Parsing performance benchmarks
- `tests/benchmarks/test_leiden_perf.py` — (NEW) Leiden performance benchmarks

## Human Notes Status
No Human Notes listed in this task.

## Docs Updated
None — no public-surface CLI/config/schema changes require README or docs updates. The `cache_dir` param in `build_pattern_catalog` is a new optional keyword argument (backward compatible; default is None, existing callers unchanged). The `content_hash` field in `FeatureRecord` is a new optional field with a default value.

## Architecture Change Proposals

### Fingerprint cache in _fingerprint_cache.py instead of fingerprint.py
- **Current constraint**: Milestone spec says "Fingerprint cache in `src/sdi/patterns/fingerprint.py`".
- **What triggered this**: Following the precedent set by `_partition_cache.py` (partition cache lives in its own module separate from `leiden.py`). Putting cache I/O in `fingerprint.py` would mix hash-computation concerns with disk I/O concerns, and would push `fingerprint.py` toward the 300-line limit.
- **Proposed change**: Cache lives in `src/sdi/patterns/_fingerprint_cache.py`. The `_fingerprint_cache.py` module imports from `fingerprint.py` (not the reverse), preserving the dependency direction.
- **Backward compatible**: Yes — no external callers of `fingerprint.py` are affected. The cache is an implementation detail.
- **ARCHITECTURE.md update needed**: No — `_fingerprint_cache.py` is an internal detail following the same pattern as `_partition_cache.py`.

### content_hash added to FeatureRecord
- **Current constraint**: CLAUDE.md says FeatureRecord fields are all required; the snapshot schema is versioned.
- **What triggered this**: Orphan cache cleanup in `assemble_snapshot` needs to know the content hash of each record without re-reading files. Rather than adding a parallel data structure or changing the `parse_repository` return type, carrying the hash in the record is the cleanest option.
- **Proposed change**: `content_hash: str = ""` with default empty string. Old snapshots that have FeatureRecords without `content_hash` deserialize cleanly via `data.get("content_hash", "")`.
- **Backward compatible**: Yes — existing snapshots deserialize correctly; existing callers of `parse_repository` receive records with `content_hash` populated.
- **ARCHITECTURE.md update needed**: No — this is a minor schema evolution within the same `snapshot_version`.

## Observed Issues (out of scope)
- `DRIFT_LOG.md` "Unresolved Observations" section contains one entry (`diff_cmd.py:54-56`) that the prior reviewer marked as resolved-by-documentation. The entry should be moved to "Resolved". Pre-existing housekeeping item; out of scope for M10.
