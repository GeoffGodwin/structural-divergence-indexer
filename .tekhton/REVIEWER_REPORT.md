## Verdict
APPROVED_WITH_NOTES

## Complex Blockers (senior coder)
- None

## Simple Blockers (jr coder)
- None

## Non-Blocking Notes
- `assembly.py:15-16` imports from `sdi.parsing._parse_cache` and `sdi.patterns._fingerprint_cache` (private, underscore-prefixed internal modules) directly rather than through each package's public `__init__` API. CLAUDE.md only prohibits `sdi/cli/` imports and circular imports, so this is not a hard violation — but crossing into a sibling package's private module is a code smell. Consider exporting `cleanup_orphan_parse_cache` from `sdi/parsing/__init__.py` and `cleanup_orphan_fingerprint_cache` from `sdi/patterns/__init__.py`.
- `read_parse_cache:53` catches `(json.JSONDecodeError, KeyError, OSError)` but not `TypeError` or `ValueError`. A corrupt cache entry whose JSON is valid but has wrong field types (e.g., `imports` is an integer) would raise `TypeError` from `list(data["imports"])` inside `FeatureRecord.from_dict`, propagating to the worker. Extremely unlikely in practice (only self-written files are in the cache), but adding `TypeError, ValueError` to the except tuple would be fully defensive.
- `test_cached_record_gets_content_hash_populated` (`test_parse_cache.py:226-235`) reads a record from cache and then manually assigns `cached.content_hash = file_hash` in the test body — the assignment is the code under test (from `_parse_one`), not behavior from `read_parse_cache`. The test exercises Python attribute assignment, not meaningful caching behavior. Not harmful but offers no real coverage.
- Benchmark tests use manual `time.perf_counter()` instead of `pytest-benchmark` fixtures. The pyproject.toml adds the `benchmark` marker but does not add `pytest-benchmark` to `[project.optional-dependencies.dev]`. The marker approach still works (no crash), but the milestone spec's stated intent was pytest-benchmark. Low priority since these tests are never run in CI.
- `test_leiden_perf.py` benchmarks call `leidenalg.find_partition` directly, bypassing SDI's `detect_communities` wrapper. This validates raw algorithm performance but does not exercise SDI's warm-start seeding path (`_partition_cache` read → `initial_membership` injection). The benchmark is still useful for the raw timing goal.

## Coverage Gaps
- No unit tests for `src/sdi/patterns/_fingerprint_cache.py` — `test_parse_cache.py` covers the parse cache thoroughly but there is no equivalent `test_fingerprint_cache.py`. The `read_fingerprint_cache`, `write_fingerprint_cache`, `cleanup_orphan_fingerprint_cache`, and `get_file_fingerprints` functions have zero explicit unit test coverage.
- `get_file_fingerprints` cache-hit path, cache-miss path, and `cache_dir=None` (caching disabled) path are not tested.
- No test covers the `assemble_snapshot` → `_cleanup_caches` integration path to verify that orphan cleanup is invoked after snapshot write and that `active_hashes` is derived correctly from `records[*].content_hash`.

## ACP Verdicts
- ACP: Fingerprint cache in `_fingerprint_cache.py` instead of `fingerprint.py` — ACCEPT — Follows the established `_partition_cache.py` precedent, keeps disk I/O out of the fingerprinting algorithm module, and preserves correct dependency direction (`_fingerprint_cache` imports from `fingerprint.py`, not the reverse). No external callers affected.
- ACP: `content_hash` added to `FeatureRecord` — ACCEPT — The `str = ""` default preserves backward compatibility with pre-M10 snapshots, `from_dict` uses `.get(..., "")`, and carrying the hash on the record avoids re-reading files during orphan cleanup. Minor schema evolution within the same `snapshot_version`.

## Drift Observations
- `assembly.py:158`, `snapshot_cmd.py:203`, and `_runner.py:152` each independently hardcode `repo_root / ".sdi" / "cache"`. Three sites for the same path with no shared constant. Centralizing as a helper or config attribute would reduce future update risk.
- `DRIFT_LOG.md` pre-existing: the unresolved `diff_cmd.py:54-56` observation (noted by the coder as out of scope) should be moved to Resolved in the next housekeeping pass.
