### Milestone 7: Snapshot Assembly, Delta Computation, and Trend Analysis

**Scope:** Build Stage 5 of the pipeline — assemble complete snapshots from all pipeline stage outputs, compute deltas between two snapshots across all four SDI dimensions, and compute trends across multiple snapshots. This is the "math" milestone — it takes raw stage outputs and produces the composite SDI metric.

**Deliverables:**
- `src/sdi/snapshot/assembly.py` with `assemble_snapshot(records, graph, metrics, community, catalog, config, commit_sha, timestamp) -> Snapshot` that combines all stage outputs into a `Snapshot` dataclass and writes JSON via atomic file operations
- `src/sdi/snapshot/delta.py` with `compute_delta(current: Snapshot, previous: Snapshot) -> DivergenceSummary` that computes all four SDI dimensions
- `src/sdi/snapshot/trend.py` with `compute_trend(snapshots: list[Snapshot], dimensions: list[str] | None) -> TrendData` for multi-snapshot trend analysis
- `tests/unit/test_delta.py`
- `tests/unit/test_trend.py`

**The four SDI dimensions in delta computation:**

| Dimension | Computation |
|---|---|
| `pattern_entropy_delta` | Per-category: current distinct shape count minus previous distinct shape count |
| `convention_drift_rate` | Net new patterns (shapes present now but not before) minus consolidated patterns (shapes present before but not now) across all categories |
| `coupling_topology_delta` | Composite of cycle count change, hub concentration change, max depth change, density change |
| `boundary_violation_velocity` | Count of new cross-boundary edges (imports crossing cluster boundaries) since previous snapshot |

**Acceptance criteria:**
- `assemble_snapshot()` produces a `Snapshot` with all required fields populated, including `snapshot_version`, `timestamp`, `commit_sha`, `config_hash`
- Snapshot JSON output is valid, self-contained, and includes all four dimension values
- `compute_delta()` returns null for all dimensions when `previous` is None (first snapshot)
- `compute_delta()` returns zero for all dimensions when current and previous are identical
- `compute_delta()` returns correct positive/negative values for known changes
- `compute_trend()` returns per-dimension time series data for the requested number of snapshots
- `compute_trend()` handles the case where the first snapshot in the range has null deltas
- Snapshot retention is enforced after assembly writes the file (calls `storage.enforce_retention()`)
- `pytest tests/unit/test_delta.py tests/unit/test_trend.py` passes

**Tests:**
- `tests/unit/test_delta.py`: Delta with no previous snapshot returns all nulls, delta with identical snapshots returns all zeros, pattern entropy delta computed correctly from known catalogs, convention drift rate computed correctly (new shapes minus lost shapes), coupling topology delta computed correctly from known graph metrics, boundary violation velocity computed from known partition changes, delta with incompatible snapshot version warns and returns null
- `tests/unit/test_trend.py`: Trend across 5 snapshots produces correct time series, trend with dimension filter returns only that dimension, trend with single snapshot (baseline) returns null series, trend correctly handles snapshots with null deltas at the start

**Watch For:**
- `convention_drift_rate` is NOT the same as `pattern_entropy_delta` — entropy delta measures the change in variety (how many distinct shapes), drift rate measures the change in conformity (net new shapes appearing minus shapes being consolidated). A codebase could have stable entropy (same number of shapes) but high drift rate (old shapes disappearing and new ones appearing at the same rate).
- `coupling_topology_delta` is a composite — define the weighting or normalization of its sub-components (cycle count change, hub concentration change, etc.) and document it. For v1, a simple sum of normalized sub-deltas is sufficient.
- `boundary_violation_velocity` requires comparing the current partition's cross-boundary edges to the previous partition's. If the partition itself changed (nodes moved to different clusters), new cross-boundary edges may appear without any new imports — this is intentional and correct (the boundary moved, so existing imports now cross it).
- `config_hash` in the snapshot should be a hash of the config values that affect analysis (not output formatting) — this allows detecting when config changes invalidate trend comparisons.

**Seeds Forward:**
- `DivergenceSummary` is included in every snapshot and is the primary output of `sdi diff`
- `TrendData` is the output of `sdi trend`
- The four dimension names (`pattern_entropy_delta`, `convention_drift_rate`, `coupling_topology_delta`, `boundary_violation_velocity`) become the enum values for `--dimension` flags in CLI commands
- Threshold checking in `sdi check` (Milestone 8) compares these delta values against config thresholds

---
