### Milestone 17: patterns.scope_exclude Config Key
<!-- milestone-meta
id: "17"
status: "pending"
-->


**Scope:** Add a new config key `[patterns] scope_exclude` (gitignore-style globs) that filters records out of pattern catalog construction *only*. Graph construction, community detection, and boundary inference are unaffected — files matched by `scope_exclude` still appear as nodes, still produce edges, and still participate in clusters and intent divergence. The motivating case: test directories where each script is intentionally varied per scenario, and including them in `pattern_entropy` / `convention_drift` inflates structural-shape counts without representing real codebase drift. Excluding them from the catalog while keeping them in the graph preserves the boundary signal (tests do depend on application code) without polluting the pattern signal.

**Philosophy reminder (read first):** Per CLAUDE.md "Safe defaults, zero mandatory config" principle, `scope_exclude` defaults to an empty list — no behavioural change unless the user opts in. Per Non-Negotiable Rule 12, this is a new config key under `[patterns]`; it does not repurpose any existing key, and its absence in old config files is normal. Per the project's data-flow rule (the five sequential pipeline stages), this milestone touches *only* Stage 4 (pattern catalog). Stages 1–3 and Stage 5 are read-only consumers. The config key name is `scope_exclude` not `tests_exclude` because the mechanism is generic — tests are the motivating case but not the only valid use (generated code, vendored snippets, fixtures, etc.).

**Deliverables:**
- Config schema in `src/sdi/config.py`:
  - Extend the `[patterns]` config dataclass with `scope_exclude: list[str] = []`.
  - Validate that every entry is a string. Non-string entries raise `SystemExit(2)` with a descriptive message naming the offending value (mirrors `core.exclude` validation).
  - Document in the config reference: "Gitignore-style glob patterns matching repo-relative POSIX paths. Records whose `file_path` matches any pattern are excluded from pattern catalog construction (Stage 4) only. They remain present in the dependency graph, the community partition, and boundary spread calculations. Default: empty list."
  - Update the default `[patterns]` block in CLAUDE.md's "Complete Default Configuration" snippet to include `scope_exclude = []` with a one-line comment.
- Filtering logic in `src/sdi/patterns/catalog.py`:
  - Compile `config.patterns.scope_exclude` to a glob matcher once at the start of `build_pattern_catalog` (`catalog.py:154-216`). Use `pathspec` if already a transitive dependency; otherwise use `fnmatch.fnmatch` against forward-slashed paths. Confirm dependency choice during implementation — do not introduce a new top-level dependency for this milestone.
  - Filter `records` by the matcher *before* the existing fingerprint extraction loop. Excluded records do not contribute to `raw[category][hash]` and do not appear in `ShapeStats.file_paths`.
  - Compile once, match per-record. Do not match per-fingerprint — the cost would be one match per pattern instance instead of one per file.
  - Counts on excluded records: track and surface the excluded file count in `PatternCatalog.to_dict()` as `meta: {"scope_excluded_file_count": N}`. This makes the exclusion visible in snapshots without affecting the metric values. The `meta` key is additive; deserializers handle its absence with `data.get("meta", {})`.
- Snapshot integration:
  - Pass `config.patterns.scope_exclude` through to `build_pattern_catalog` (the existing call site in the snapshot CLI command should already pass `config`; verify and add the parameter if missing).
  - The `Snapshot.pattern_catalog` JSON gains `meta.scope_excluded_file_count` when applicable; older snapshots without this field deserialize correctly.
- CLI surface (`src/sdi/cli/show_cmd.py`):
  - When `meta.scope_excluded_file_count > 0`, render a one-line note in `sdi show` text output: `Pattern catalog excluded N file(s) via patterns.scope_exclude.` No color, no warning level — this is informational.
- Documentation:
  - In `docs/ci-integration.md`, add a brief subsection: "Excluding test directories from the pattern catalog" with a worked TOML example:
    ```toml
    [patterns]
    scope_exclude = [
      "tests/**",
      "test/**",
      "**/__tests__/**",
      "**/*.test.ts",
      "**/*.spec.ts",
    ]
    ```
    and a one-paragraph note that excluded files remain in the graph and partition, so coupling and boundary metrics still reflect them.
  - Add a `CHANGELOG.md` entry: `Added: patterns.scope_exclude config key for filtering files out of the pattern catalog while keeping them in the dependency graph.`

**Acceptance criteria:**
- A snapshot of a fixture with `scope_exclude = ["tests/**"]` reports zero pattern instances in `pattern_catalog.categories[*].shapes[*].file_paths` for any path under `tests/` — assert by enumerating `file_paths` across all shapes and checking the prefix.
- The same snapshot reports unchanged `graph_metrics.node_count`, `graph_metrics.edge_count`, and `partition_data.cluster_count` compared to a snapshot of the same fixture with `scope_exclude = []`. The graph is unaffected.
- `pattern_catalog.meta.scope_excluded_file_count` equals the number of records whose path matched any pattern.
- A snapshot with `scope_exclude = []` (default) is byte-identical to a pre-M17 snapshot of the same fixture except for the addition of an empty-or-absent `meta` block. Use a reference-snapshot regression check.
- Glob matching follows gitignore semantics: `**/` matches any directory depth, `*` matches any path segment without slashes, leading `/` anchors to repo root. Verify with at least these cases:
  - `tests/**` matches `tests/foo.py`, `tests/sub/bar.py`; does not match `nottests/foo.py`.
  - `**/*.test.ts` matches `src/foo.test.ts` and `src/util/bar.test.ts`; does not match `src/foo.ts`.
  - `/scripts/setup.sh` (anchored) matches only the top-level `scripts/setup.sh`, not `lib/scripts/setup.sh`.
- Invalid glob entries (e.g., `[unclosed`) raise `SystemExit(2)` at config load time with a message naming the offending pattern.
- Non-string entries (e.g., `scope_exclude = [42]`) raise `SystemExit(2)` at config load time, mirroring `core.exclude` validation behaviour.
- Determinism: two `sdi snapshot` runs with the same `scope_exclude` configuration produce byte-identical pattern catalogs. The matcher must produce stable matches regardless of `dict` / `set` iteration order.

**Tests:**

- `tests/unit/test_config.py` — extend with:
  - `scope_exclude` defaults to `[]` when absent in `.sdi/config.toml`.
  - non-string entries raise `SystemExit(2)`.
  - invalid glob patterns raise `SystemExit(2)` with the offending pattern in the message.
  - valid `scope_exclude = ["tests/**", "**/*.test.ts"]` parses without error.
- `tests/unit/test_catalog.py` — extend with:
  - `build_pattern_catalog` excludes records matching `scope_exclude` patterns from pattern instance accumulation.
  - excluded records do not appear in `ShapeStats.file_paths` for any shape.
  - `meta.scope_excluded_file_count` equals the number of records dropped by the filter.
  - `meta` block is absent from `to_dict()` output when no records were excluded (keep the default JSON quiet).
  - glob anchoring: `/scripts/setup.sh` matches only the top-level path; nested matches are excluded from the match set.
- `tests/integration/test_full_pipeline.py` — extend with:
  - new fixture `tests/fixtures/scope-exclude-shell/` containing `lib/util.sh` (one canonical pattern), `cmd/run.sh` (one variant pattern), and `tests/scenario_a.sh`, `tests/scenario_b.sh`, `tests/scenario_c.sh` (each a different `error_handling` variant).
  - run with `scope_exclude = []`: `pattern_entropy` includes 5 distinct shapes.
  - run with `scope_exclude = ["tests/**"]`: `pattern_entropy` includes 2 distinct shapes (the canonical and the one variant from non-test code), and `graph_metrics.edge_count` and `partition_data.cluster_count` match the unfiltered run.
- `tests/integration/test_cli_output.py` — extend with one case asserting the informational line `Pattern catalog excluded N file(s) via patterns.scope_exclude.` appears in `sdi show` output when `N > 0` and is absent when `N == 0`.

**Watch For:**
- **Filter applies to Stage 4 only.** Reviewers may suggest filtering at parsing or graph stages — that breaks the design intent. Files in `scope_exclude` must remain in `FeatureRecord` lists, in `path_to_id`, in the graph, and in the partition. The filter is applied *only* at `build_pattern_catalog` entry.
- **Glob semantics are gitignore-style, not regex.** Use the same matcher SDI already uses for `core.exclude` (consistency matters more than feature parity with `.gitignore`'s full edge cases). Confirm during implementation which matcher is used; do not introduce a new dependency to add `.gitignore` semantics not already present.
- **Path normalization.** Match against forward-slashed repo-relative paths. The matcher must not be sensitive to OS path separators — `tests\foo.py` on Windows and `tests/foo.py` on Linux must produce the same match result. This is shared with `core.exclude` and should reuse the same normalization helper.
- **Reflect the exclusion in output, do not hide it.** `meta.scope_excluded_file_count` is mandatory when `> 0`. Silent exclusion would let users be confused about why their `pattern_entropy` looks lower than expected.
- **No automatic test detection.** Do not auto-detect test directories. Per CLAUDE.md "automated inference, human ratification" — boundaries are inferred and proposed, but config keys are explicit. `scope_exclude` is a user-declared list; SDI never guesses what the user considers tests.
- **`scope_exclude` does NOT alias `core.exclude`.** They have different semantics: `core.exclude` removes files from discovery entirely; `scope_exclude` keeps them in the graph but removes them from the catalog. Do not consolidate. The CLAUDE.md docs must clarify the distinction.
- **Pattern matching cost is bounded.** Match per record (Stage 1 output count), not per fingerprint. With even 10k files and 10 patterns, that is 100k `fnmatch` calls — sub-second. Per-fingerprint matching scales with pattern instance count (potentially millions) and is the slow path; reject any reviewer suggestion to move the matcher inside the fingerprint loop.
- **Config-hash impact.** `_compute_config_hash` (`src/sdi/snapshot/assembly.py:33-62`) hashes `config.patterns.categories` and `config.patterns.min_pattern_nodes`. Add `scope_exclude` (sorted) to the same dict so changing the exclusion list invalidates the snapshot's config hash and signals to `sdi diff` consumers that the configuration that produced these snapshots differed.
- **Gitignore-style does not include negation by default.** A leading `!` to un-exclude is *not* required in scope. If `pathspec` provides it for free, fine; do not implement custom negation logic in this milestone.

**Seeds Forward:**
- Closes the most common noise-source on shell-heavy and JS/TS-heavy repos: deliberately-varied test files inflating `pattern_entropy`.
- Provides the validation harness in M18 a clean way to run pattern-catalog assertions on real repos with test directories — without `scope_exclude`, the harness invariants would have to be calibrated to per-repo test structure.
- Establishes the precedent for per-stage scoping config keys. Future milestones may add `boundaries.scope_exclude` or similar; M17 does not introduce them, but the naming convention now exists.

---
