# Human Action Required

The pipeline identified items that need your attention. Review each item
and check it off when addressed. The pipeline will display a banner until
all items are resolved.

## Action Items
- [ ] [2026-04-11 | Source: architect] `src/sdi/graph/metrics.py:126` — `graph.simple_cycles()` has exponential worst-case time and space complexity in the number of cycles. Acceptable for v1 on real codebases where true cycles are rare. This item should be added to the pre-1.0 hardening backlog with a concrete resolution path: introduce a configurable cycle-count cap (e.g., stop enumeration after N cycles) or a node-count guard above which cycle detection is skipped and a warning is emitted. No code change in this cycle; requires a scope decision from the project owner on the acceptable cap value and user-facing behavior. ---
