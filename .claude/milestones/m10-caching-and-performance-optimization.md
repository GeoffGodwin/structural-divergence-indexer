### Milestone 10: Caching and Performance Optimization
<!-- milestone-meta
id: "10"
status: "done"
-->


**Scope:** Implement the parse cache (keyed by file content hash) and fingerprint cache to make incremental snapshots near-instant when few files change. Add orphan cache cleanup. Verify performance targets (< 30s for 10K–100K LOC projects).

**Deliverables:**
- Parse cache in `src/sdi/parsing/__init__.py`: compute SHA-256 of file bytes, check `.sdi/cache/parse_cache/<hash>.json` before parsing, write cache entry after parsing
- Fingerprint cache in `src/sdi/patterns/fingerprint.py`: cache pattern fingerprint results per file content hash in `.sdi/cache/fingerprints/<hash>.json`
- Orphan cache cleanup: after snapshot capture, remove cache entries whose content hash does not correspond to any current file
- Performance validation against test fixtures at various scales

**Acceptance criteria:**
- Second run of `sdi snapshot` on an unchanged codebase completes significantly faster than the first (parse cache hit)
- Cache files are keyed by SHA-256 of file content — changing a file invalidates only that file's cache entry
- Cache is transparent — results are identical whether cache is hit or missed
- Orphan cache entries (files that no longer exist or have changed) are cleaned up after each snapshot
- Cache files use atomic writes
- `SDI_WORKERS=1` still works correctly with caching enabled
- Deleting `.sdi/cache/` entirely triggers a full re-parse with no errors (cold start)

**Tests:**
- `tests/unit/test_parse_cache.py`: Cache hit returns same FeatureRecord as fresh parse, cache miss triggers parse and writes cache, changed file invalidates cache (different hash), orphan cleanup removes stale entries, corrupt cache file triggers re-parse (not error)
- `tests/benchmarks/test_parsing_perf.py`: Measure parse time at 100, 1000, and 5000 file scales (synthetic), verify cache speedup
- `tests/benchmarks/test_leiden_perf.py`: Measure Leiden time at 100, 1000, 5000, and 10000 node graph scales

**Watch For:**
- SHA-256 hashing of file bytes is the cache key — not the file path. Renamed files with identical content hit the same cache entry (this is correct behavior).
- Cache files must be written atomically (tempfile + `os.replace`) just like snapshot files
- Orphan cleanup must not delete cache entries for files that are still present but unchanged — only entries whose hash is not found in the current file set
- Benchmark tests should NOT run in normal CI — gate them behind `pytest.mark.benchmark` or a separate test target

**Seeds Forward:**
- Caching makes `sdi snapshot` fast enough for CI use on medium projects (target: < 30s)
- The cache infrastructure (content-addressed storage with atomic writes) could be reused for other cached artifacts in post-v1

---
