## Test Audit Report

### Audit Summary
Tests audited: 1 file (`tests/unit/test_leiden_internals.py`), 23 test functions
Verdict: CONCERNS

---

### Findings

#### INTEGRITY: Failing test left in suite with unfixed implementation bug
- File: tests/unit/test_leiden_internals.py:234
- Issue: `test_read_cache_toplevel_array_returns_none` asserts `result is None`,
  but `_partition_cache.py:_read_cache` currently raises `AttributeError` for
  this input. When `partition.json` contains a top-level JSON array
  (e.g. `[1, 2, 3]`), `json.load()` succeeds and returns a `list`. The next
  statement calls `data.get("cache_version")` (line 45), which raises
  `AttributeError` because lists do not have `.get()`. The `except` clause at
  `_partition_cache.py:48` catches only `(json.JSONDecodeError, OSError,
  KeyError)` — `AttributeError` is not included. The tester documented the bug
  in TESTER_REPORT.md and wrote the test to expose it, but the implementation
  was not fixed. The test itself is honest and correctly states the required
  contract (corrupt/unrecognised cache → cold start, return `None`). The test
  suite is left in a failing state (22 pass, 1 fail per TESTER_REPORT.md).
- Severity: HIGH
- Action: Fix `src/sdi/detection/_partition_cache.py:_read_cache`. After
  `data = json.load(fh)`, add `if not isinstance(data, dict): return None`
  before the `data.get()` call on the next line. This is the correct fix;
  adding `AttributeError` to the except tuple is an acceptable but weaker
  alternative. Do not change the test.

#### COVERAGE: `test_surface_area_ratios_boundary_edges` omits cluster-1 assertion
- File: tests/unit/test_leiden_internals.py:341
- Issue: The test builds edges `(0→1)`, `(1→2)`, `(2→3)` with partition
  `[0, 0, 1, 1]`. Both clusters are symmetrically affected by the single
  boundary crossing at `(1→2)`: cluster 0 has 2 total edges (internal `0→1`,
  external `1→2`) → ratio 0.5; cluster 1 has 2 total edges (external `1→2`,
  internal `2→3`) → ratio 0.5. Only `ratios[0]` is asserted. A future
  regression that broke cluster-1 edge accounting would pass this test
  silently.
- Severity: LOW
- Action: Add `assert ratios[1] == pytest.approx(0.5)` immediately after the
  existing assertion at line 347.

---

### Rubric Notes (no findings)

**Assertion Honesty** — All assertions derive expected values from traceable
algorithm logic. Values such as `0`, `1`, `2`, `0.5`, and `1.0` all correspond
to explicit partition assignments and edge counts in the test fixtures.
`pytest.approx` is used correctly for floating-point comparisons.
No hard-coded magic numbers are present that cannot be independently
re-derived from the test inputs.

**Edge Case Coverage** — Comprehensive. Covered: cold start (no prev_cache),
warm start, flicker reset, new-node immediate acceptance, candidate switch
(counter resets to 1), half-changed stability score, new nodes excluded from
stability score, corrupt JSON cache, missing cache file, top-level JSON array
cache (the identified bug), missing `vertex_names` key, missing
`stable_partition` key, disconnected graph (no cross-cluster edges),
non-contiguous cluster IDs (debounce mid-transition), and zero-edge cluster
(surface area ratio 0.0). The ratio of error-path to happy-path tests is
approximately 1:1.

**Implementation Exercise** — All 23 tests call the real implementation.
No function under test is mocked. Filesystem tests (`test_cache_round_trip`,
`test_read_cache_*`, `test_write_cache_creates_directory`) use the `tmp_path`
pytest fixture to exercise real `Path` and `json` I/O. `igraph.Graph` objects
are constructed in-process without stubbing.

**Test Weakening** — Not present. The rework-cycle changes documented in
CODER_SUMMARY.md strengthened the suite: `test_surface_area_ratios_empty_cluster`
now asserts `set(ratios.keys()) == {0, 2}` (previously masked a bug by passing
an incorrect `cluster_count=3` argument), and `test_surface_area_ratios_non_contiguous_ids`
was added to prevent regressions on non-contiguous partition IDs. No assertion
was broadened or removed.

**Test Naming** — All names follow `test_<scenario>_<expected_outcome>` or
equivalent conventions. Representative examples:
`test_debounce_flicker_resets_counter`,
`test_read_cache_toplevel_array_returns_none`,
`test_build_initial_membership_missing_vertex_names_raises`,
`test_surface_area_ratios_non_contiguous_ids`. No generic `test_1` or
`test_thing` style names.

**Scope Alignment** — All imported symbols exist in the current codebase:
`PARTITION_CACHE_VERSION`, `_apply_debounce`, `_build_initial_membership`,
`_compute_stability_score`, `_read_cache`, `_write_cache` from
`sdi.detection._partition_cache`; `_compute_inter_cluster_edges`,
`_compute_surface_area_ratios` from `sdi.detection.leiden`. No orphaned,
stale, or renamed references.

**Test Isolation** — All filesystem interactions use `tmp_path`. No test reads
live project files, pipeline reports, build artifacts, or other mutable
project state. Every test constructs its own fixture data in-process via the
`_make_graph` and `_prev_cache` helpers defined at the top of the file.
