# Architecture Decision Log

Accepted Architecture Change Proposals are recorded here for institutional memory.
Each entry captures why a structural change was made, preventing future developers
(or agents) from reverting to the old approach without understanding the context.

## ADL-1: Fingerprint cache in `_fingerprint_cache.py` instead of `fingerprint.py` (Task: "Implement Milestone 10: Caching and Performance Optimization")
- **Date**: 2026-04-24
- **Rationale**: Follows the established `_partition_cache.py` precedent, keeps disk I/O out of the fingerprinting algorithm module, and preserves correct dependency direction (`_fingerprint_cache` imports from `finge
- **Source**: Accepted ACP from pipeline run

## ADL-2: `content_hash` added to `FeatureRecord` (Task: "Implement Milestone 10: Caching and Performance Optimization")
- **Date**: 2026-04-24
- **Rationale**: The `str = ""` default preserves backward compatibility with pre-M10 snapshots, `from_dict` uses `.get(..., "")`, and carrying the hash on the record avoids re-reading files during orphan cleanup. Min
- **Source**: Accepted ACP from pipeline run

## ADL-3: Extract JS/TS helpers to `_js_ts_resolver.py` (Task: "M15")
- **Date**: 2026-04-26
- **Rationale**: The extraction is warranted: builder.py was 455 lines pre-M15 and would have exceeded 300 again with shell additions. All names are re-exported for backward compatibility, the module carries a leading
- **Source**: Accepted ACP from pipeline run
