# Security Notes

Generated: 2026-04-11 08:36:32

## Non-Blocking Findings (MEDIUM/LOW)
- [LOW] [category:A05] [src/sdi/graph/metrics.py:130] fixable:yes — `graph.simple_cycles()` has exponential worst-case time complexity (O((n+e) * cycle_count)). For a dense, adversarially constructed dependency graph this could cause resource exhaustion during analysis. In practice SDI operates on real codebases where cycle counts are bounded, but if FeatureRecords are ever accepted from untrusted external sources a cycle count cap should be added (e.g., short-circuit after N cycles and return the cap value with a warning).
