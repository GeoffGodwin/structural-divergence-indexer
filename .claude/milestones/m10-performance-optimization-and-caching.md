### Milestone 10: Performance Optimization and Caching

**Scope:** Optimize the full pipeline for CI performance targets. Implement incremental analysis (parse cache, fingerprint cache), benchmark against target codebase sizes, and profile bottlenecks. This milestone ensures SDI meets the hard CI performance requirements: <5s for small, <30s for medium, <2min for large codebases.

**Deliverables:**
- Parse cache optimization: content-addressed feature cache in `.sdi/cache/parse_cache/`, keyed by SHA-256 of file content
- Fingerprint cache: content-addressed pattern fingerprint cache in `.sdi/cache/fingerprints/`
- Cache invalidation: orphaned entries cleaned up during `sdi snapshot` (entries older than retention window)
- ProcessPoolExecutor tuning: optimal worker count selection, chunking strategy for file batches
- Benchmark suite: pytest-benchmark tests for parsing, graph construction, Leiden, fingerprinting at 100, 1K, 5K, 10K node scales
- Performance profiling documentation: how to profile SDI and interpret results
- Memory optimization: verify CST-per-file-then-discard pattern holds under all code paths

**Files to create or modify:**
- `src/sdi/parsing/discovery.py` (cache integration)
- `src/sdi/parsing/__init__.py` (cache-aware orchestration)
- `src/sdi/patterns/fingerprint.py` (fingerprint cache)
- `src/sdi/snapshot/assembly.py` (cache cleanup)
- `tests/benchmarks/test_parsing_perf.py`
- `tests/benchmarks/test_leiden_perf.py`
- `.github/workflows/benchmarks.yml`

**Acceptance criteria:**
- Second run of `sdi snapshot` on unchanged codebase is >5x faster than first run (cache hits)
- Parse cache hit rate is ~100% for unchanged files
- Cache cleanup removes orphaned entries without removing active entries
- Benchmark results for 1K-file synthetic project: total pipeline under 10 seconds
- Benchmark results for 5K-file synthetic project: total pipeline under 60 seconds
- Memory usage stays proportional to largest single file, not total codebase size (verified by profiling)
- `SDI_WORKERS=1` forces single-process parsing (useful for debugging)
- Cache directory size stays bounded (orphan cleanup works)
- `.github/workflows/benchmarks.yml` runs benchmarks on release tags

**Tests:**
- `tests/benchmarks/test_parsing_perf.py`:
  - Parse 100 synthetic Python files: record time
  - Parse 1,000 synthetic files: record time
  - Parse 5,000 synthetic files: record time
  - Second parse (all cached): record time, verify >5x speedup
- `tests/benchmarks/test_leiden_perf.py`:
  - Leiden on 100-node random graph: record time
  - Leiden on 1,000-node random graph: record time
  - Leiden on 5,000-node random graph: record time
  - Leiden on 10,000-node random graph: record time

**Watch For:**
- Content-addressed caching means the cache key is the file content hash, not the file path. A renamed file with identical content should hit the cache.
- Cache files must be written atomically (same tempfile + rename pattern). Two concurrent `sdi snapshot` runs writing to the same cache must not corrupt entries.
- `ProcessPoolExecutor` startup cost is non-trivial. For very small projects (<20 files), single-process parsing may be faster. Consider a threshold.
- Benchmarks must use synthetic, deterministic test data — not real repos that might change.
- Memory profiling: use `tracemalloc` or `memory_profiler` to verify peak memory stays bounded.

**Seeds Forward:**
- Performance benchmarks establish the regression baseline for all future releases.
- Cache infrastructure is the foundation for any future incremental analysis optimizations.
- Worker tuning data informs the default `SDI_WORKERS` value.

---
