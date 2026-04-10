### Milestone 8: CLI Commands — snapshot, show, diff, trend, check, catalog

**Scope:** Wire the full analysis pipeline into the CLI commands. Implement `sdi snapshot` (full pipeline execution), `sdi show`, `sdi diff`, `sdi trend`, `sdi check`, and `sdi catalog` with all flags, output formats (text/json/csv), and exit codes. This is the integration milestone — each command orchestrates the pipeline stages from previous milestones.

**Deliverables:**
- `src/sdi/cli/snapshot_cmd.py` — full pipeline orchestration: parse → graph → leiden → patterns → assemble → write
- `src/sdi/cli/show_cmd.py` — read most recent snapshot, display summary
- `src/sdi/cli/diff_cmd.py` — compare two snapshots, display delta
- `src/sdi/cli/trend_cmd.py` — compute and display multi-snapshot trends with `--last`, `--dimension`, `--format csv`
- `src/sdi/cli/check_cmd.py` — CI gate with threshold checking and exit code 10
- `src/sdi/cli/catalog_cmd.py` — display pattern catalog with `--category` filter
- Rich-formatted text output for human mode (tables, colored deltas, sparklines for trends)
- JSON output for machine mode (valid, self-contained documents)
- CSV output for `sdi trend --format csv`
- Progress indicators on stderr (parsing progress bar, graph analysis spinner) via Rich

**Acceptance criteria:**
- `sdi snapshot` on `simple-python` fixture produces a valid snapshot JSON file in `.sdi/snapshots/`
- `sdi snapshot --commit HEAD` reads files at HEAD without modifying the working tree (uses `git show`)
- `sdi snapshot --output /tmp/test.json` writes to the specified path
- `sdi snapshot --format summary` prints human-readable summary to stdout
- `sdi show` displays the most recent snapshot summary
- `sdi show --format json | jq '.'` produces valid JSON
- `sdi diff` compares the two most recent snapshots
- `sdi diff SNAPSHOT_A SNAPSHOT_B` compares two specified snapshots
- `sdi trend --last 5` shows trend data for the 5 most recent snapshots
- `sdi trend --format csv` produces valid CSV output
- `sdi trend --dimension pattern_entropy` filters to one dimension
- `sdi check` exits 0 when all dimensions are within thresholds
- `sdi check` exits 10 when any dimension exceeds its threshold, printing which ones
- `sdi check --threshold 0.0` forces exit 10 on any non-zero change
- `sdi check --dimension boundary_violations` checks only one dimension
- `sdi catalog` displays all pattern categories with shape counts
- `sdi catalog --category error_handling` filters to one category
- All progress output goes to stderr; all data goes to stdout
- `--no-color` and `NO_COLOR=1` disable colored output
- `--quiet` suppresses progress indicators
- All existing unit tests continue to pass

**Tests:**
- `tests/integration/test_cli_output.py`: Capture stdout/stderr for each command, verify format correctness, verify exit codes, verify JSON validity, verify CSV validity
- `tests/integration/test_full_pipeline.py`: Run `sdi init` → `sdi snapshot` → `sdi show` → `sdi catalog` on `simple-python` fixture, verify end-to-end output
- `tests/unit/test_check_cmd.py`: Threshold comparison logic, per-dimension override application (including expired overrides), exit code 10 vs 0

**Watch For:**
- `sdi snapshot --commit REF` must use `git show REF:path` to read files — it must NEVER run `git checkout` or modify the working tree (Critical System Rule 9)
- Rich progress bars default to stdout — must explicitly use `Console(stderr=True)` for all Rich output
- JSON output from `--format json` must be a single valid JSON document, not streaming JSON lines
- `sdi check` is the only command that may exit with code 10 — ensure no other command accidentally returns 10
- When there are no previous snapshots, `sdi diff` should print a message ("only one snapshot exists") and exit 0, not error
- `sdi trend` with fewer snapshots than `--last N` should use all available snapshots, not error

**Seeds Forward:**
- CLI commands are the public API — flag names and output formats become the user-facing contract
- `sdi check` exit code 10 is used by CI pipelines and git hooks in Milestone 10
- `sdi snapshot --commit REF` capability enables the historical backfill scripting workflow (documented in post-v1 scope)

---
