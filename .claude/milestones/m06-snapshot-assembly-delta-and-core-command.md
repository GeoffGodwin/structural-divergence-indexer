### Milestone 6: Snapshot Assembly, Delta, and Core Commands

**Scope:** Implement Stage 5 of the pipeline: snapshot assembly from all stage outputs, delta computation between two snapshots, snapshot storage with atomic writes and retention enforcement, and the `sdi snapshot`, `sdi diff`, `sdi show`, and `sdi trend` commands. This is the integration milestone that ties the entire pipeline together into working end-to-end commands.

**Deliverables:**
- `Snapshot` dataclass containing: metadata (timestamp, commit SHA, snapshot_version), graph metrics, cluster assignments + stability, pattern catalog + entropy, boundary intent divergence (if boundary spec exists)
- `DivergenceSummary` dataclass containing the four SDI dimensions: pattern entropy delta, convention drift rate, coupling topology delta, boundary violation velocity
- Snapshot JSON serialization/deserialization with `snapshot_version` field
- Delta computation across all four dimensions between two snapshots
- Snapshot storage: atomic write (tempfile + os.replace), filename format `<timestamp>-<short-sha>.json`, retention enforcement
- `sdi snapshot` command: runs full pipeline (Stages 1–5), writes JSON, prints human summary
- `sdi diff` command: compares two snapshots (or two most recent), text and JSON output
- `sdi show` command: displays most recent snapshot data, current boundaries, pattern summary
- `sdi trend` command: trajectory across multiple snapshots, text/JSON/CSV output, sparkline display
- Full pipeline orchestration: calls parsing → graph → detection → patterns → assembly in sequence
- Signal handling: SIGINT/SIGTERM clean shutdown, discard incomplete snapshot
- Progress indicators via Rich (stderr only)

**Files to create or modify:**
- `src/sdi/snapshot/__init__.py`
- `src/sdi/snapshot/model.py`
- `src/sdi/snapshot/assembly.py`
- `src/sdi/snapshot/delta.py`
- `src/sdi/snapshot/storage.py`
- `src/sdi/snapshot/trend.py`
- `src/sdi/cli/snapshot_cmd.py`
- `src/sdi/cli/diff_cmd.py`
- `src/sdi/cli/show_cmd.py`
- `src/sdi/cli/trend_cmd.py`
- `tests/unit/test_snapshot_model.py`
- `tests/unit/test_delta.py`
- `tests/unit/test_storage.py`
- `tests/unit/test_trend.py`
- `tests/integration/test_full_pipeline.py`
- `tests/integration/test_multi_snapshot.py`

**Acceptance criteria:**
- `sdi snapshot` on `tests/fixtures/simple-python/` produces a valid JSON snapshot file in `.sdi/snapshots/`
- Snapshot filename follows `<YYYYMMDDTHHMMSS>-<short-sha>.json` format
- Snapshot JSON includes `snapshot_version`, timestamp, commit SHA, all four SDI dimensions, graph metrics, pattern catalog summary, cluster assignments
- `sdi snapshot --commit HEAD~3` analyzes a historical commit
- `sdi snapshot --format json` writes JSON only (no summary to stdout)
- `sdi snapshot --format summary` prints summary only (no JSON file)
- `sdi diff` with no args compares two most recent snapshots
- `sdi diff snapshot_a.json snapshot_b.json` compares two specific snapshots
- `sdi diff --format json` produces machine-readable delta
- `sdi show` prints current state with most recent snapshot summary
- `sdi show --verbose` includes full pattern catalog and boundary details
- `sdi trend --last 20` shows trajectory of all dimensions over last 20 snapshots
- `sdi trend --dimension pattern_entropy` filters to one dimension
- `sdi trend --format csv` outputs valid CSV
- Snapshot retention: after writing snapshot 101 (with retention=100), the oldest is deleted
- Atomic writes: interrupting `sdi snapshot` mid-write does not leave partial files
- SIGINT during snapshot cleanly exits without corrupting state
- Progress bar appears on stderr during parsing (suppressed with `--quiet`)
- First snapshot has null deltas (baseline)
- Second snapshot computes correct deltas against first
- Incompatible snapshot version triggers a warning and baseline treatment

**Tests:**
- `tests/unit/test_snapshot_model.py`:
  - Snapshot serializes to JSON and deserializes back identically
  - `snapshot_version` field is always present
  - Null deltas on first snapshot
- `tests/unit/test_delta.py`:
  - Pattern entropy delta: added shapes increase, removed shapes decrease
  - Convention drift rate: net new patterns minus consolidated patterns
  - Coupling topology delta: cycle count change, hub concentration change, depth change
  - Boundary violation velocity: new cross-boundary edges since previous
  - Incompatible snapshot versions produce warning, return null delta
- `tests/unit/test_storage.py`:
  - Atomic write: file appears fully formed or not at all
  - Retention enforcement deletes oldest when count exceeds limit
  - Snapshot filename format is correct
  - Snapshots are listed in chronological order
- `tests/unit/test_trend.py`:
  - Trend across N snapshots produces N data points per dimension
  - `--last` limits to most recent N
  - Single snapshot produces valid (but uninteresting) trend
- `tests/integration/test_full_pipeline.py`:
  - Run `sdi snapshot` on `simple-python` fixture, verify snapshot contents
  - Run on fixture with no Python files, verify exit code 3
  - Run on fixture with mixed supported/unsupported languages, verify partial analysis
- `tests/integration/test_multi_snapshot.py`:
  - `sdi init` → `sdi snapshot` → modify fixture → `sdi snapshot` → `sdi diff` → verify correct deltas
  - `sdi trend` across 5 snapshots shows correct trajectory

**Watch For:**
- Snapshot timestamp must use UTC, not local time. Use `datetime.datetime.now(datetime.UTC).isoformat()`.
- `--commit` flag requires checking out a git ref. Use `git show` or `git archive` to access files at a specific commit — do NOT use `git checkout` which modifies the working tree.
- JSON serialization of `igraph` objects is not automatic. Extract relevant data into plain dicts/lists before serialization.
- Rich progress bars write to stderr by default (correct), but some Rich features may write to stdout. Explicitly pass `console=Console(stderr=True)` for all Rich output.
- Convention drift rate is "net new patterns minus consolidated patterns" — this is a signed value. Positive means more patterns were introduced than removed. Clarify sign convention in the snapshot schema.
- CSV output for `sdi trend` must have a header row with column names, despite the DESIGN.md saying "headerless." Headerless CSV is ambiguous — include headers for usability. (Note: this is an implementation decision not explicitly resolved in DESIGN.md.)

**Seeds Forward:**
- Snapshot JSON schema is the public API of the tool. Its structure must be stable from this point forward within the major version.
- `DivergenceSummary` is used by `sdi check` (Milestone 8) for threshold comparison.
- The full pipeline orchestration function is the entry point that `sdi check` and git hooks call.
- Trend computation is the basis for rate-of-change alerting in `sdi check`.

---
