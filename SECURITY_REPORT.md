## Summary
M04 adds three new source modules (`src/sdi/graph/__init__.py`, `builder.py`, `metrics.py`) and two test files implementing Stage 2 of the SDI pipeline: dependency graph construction and structural metric computation. The change is purely analytical — no file I/O, no network calls, no shell execution, no authentication surfaces, and no user-facing input validation boundaries. Input arrives as internal `FeatureRecord` objects from Stage 1 parsing. The implementation is structurally clean and presents no meaningful attack surface.

## Findings

- [LOW] [category:A05] [src/sdi/graph/metrics.py:130] fixable:yes — `graph.simple_cycles()` has exponential worst-case time complexity (O((n+e) * cycle_count)). For a dense, adversarially constructed dependency graph this could cause resource exhaustion during analysis. In practice SDI operates on real codebases where cycle counts are bounded, but if FeatureRecords are ever accepted from untrusted external sources a cycle count cap should be added (e.g., short-circuit after N cycles and return the cap value with a warning).

## Verdict
FINDINGS_PRESENT
