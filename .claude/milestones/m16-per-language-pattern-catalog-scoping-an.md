### Milestone 16: Per-Language Pattern Catalog Scoping and Signals
<!-- milestone-meta
id: "16"
status: "done"
-->


**Scope:** Make the pattern catalog and divergence signals meaningful on mixed-language codebases by attaching applicable-languages metadata to every category and surfacing per-language entropy and convention drift alongside the existing language-agnostic aggregate. Today, `_catalog_pattern_entropy` and `_catalog_convention_drift` (`src/sdi/snapshot/delta.py:29-67`) sum across all categories and all languages; on a 95%-shell repo with 28 Python files, the same `error_handling` category aggregates a Python `try/except` shape and a shell `set -e` shape into one number, and three Python-only categories (`class_hierarchy`, `context_managers`, `comprehensions`) appear in the report with `entropy=0`. Per-language signals make drift interpretable in the dimension that actually changed.

**Philosophy reminder (read first):** Per CLAUDE.md Non-Negotiable Rule 4, SDI never classifies code as good or bad. This milestone adds *scoping* metadata, not *quality* metadata — a category being "applicable to language X" is a structural property (the AST construct exists in X), not a value judgment. Phrases like "language-appropriate," "irrelevant," "doesn't apply," or "unsupported" are fine; "improper," "wrong-language," or "polluted" are not. Per Rule 12, config keys are never repurposed: `pattern_entropy` and `convention_drift` keep their existing semantics. New per-language fields are *additive* — they do not replace the aggregate.

**Deliverables:**
- `src/sdi/patterns/categories.py`:
  - Add a `languages: frozenset[str]` field to `CategoryDefinition` (`categories.py:25-38`). Default to an empty frozenset; categories with an empty `languages` set are treated as "applies to all languages" for back-compat.
  - Populate `languages` for each built-in category in `_build_registry()` (`categories.py:94-107`):
    - `error_handling`: `frozenset({"python", "shell", "javascript", "typescript", "go", "java", "rust"})` (every supported language has try/except, set -e, panic/recover, throw, Result, etc.)
    - `data_access`: `frozenset({"python", "shell", "javascript", "typescript", "go", "java", "rust"})` (call-site allow-lists exist for every language; absence of a query string for a language means zero detection but the category remains applicable in principle).
    - `logging`: same set as `data_access`.
    - `async_patterns`: `frozenset({"python", "shell", "javascript", "typescript", "go", "rust"})` (Java omitted — `tree-sitter-java` async detection is out of scope for v0; CompletableFuture and friends are not in the catalog).
    - `class_hierarchy`: `frozenset({"python", "javascript", "typescript", "java"})` — Go (no inheritance, just embedding), Rust (traits, not classes), and shell (no classes) are excluded.
    - `context_managers`: `frozenset({"python"})` — Python `with` only. JavaScript `using` (TC39 stage 3 at the time of writing) is not yet detected by SDI's queries; if a future milestone adds a TS/JS query, expand this set in that milestone.
    - `comprehensions`: `frozenset({"python"})` — Python list/dict/set/generator comprehensions only. JavaScript array methods (`.map`, `.filter`) are not comprehensions and are out of scope.
  - Document the rule in a module docstring update: "An empty `languages` set means the category applies to every parsed language. A non-empty set restricts catalog rollups for that category to those languages — files in non-applicable languages cannot contribute instances even if a future adapter mistakenly emits them."
  - Add `def applicable_languages(category: str) -> frozenset[str] | None` returning `None` for unknown categories (consistent with `get_category` returning `None`).
- `src/sdi/patterns/catalog.py`:
  - In `build_pattern_catalog` (`catalog.py:154-216`), filter pattern-instance contributions by category language scope:
    - Resolve each record's language once.
    - For each fingerprint emitted by `get_file_fingerprints`, check `category_def.languages`. If the set is non-empty and `record.language` is not in it, drop the fingerprint silently (it is a programming error in the adapter, not user-facing). Continue otherwise.
  - Add a `category_languages: dict[str, list[str]]` field to `PatternCatalog.to_dict()` mirroring `categories.py` registration. Sort each list for deterministic output.
- New per-language rollup helpers in `src/sdi/snapshot/delta.py`:
  - `_per_language_pattern_entropy(catalog_dict, language_breakdown) -> dict[str, float]` returning `{ language: distinct_shape_count_for_categories_applicable_to_language }`. The denominator is "categories scoped to this language," not "categories present in catalog."
  - `_per_language_convention_drift(catalog_dict, records_or_lang_index) -> dict[str, float]` — same shape as `_catalog_convention_drift` but partitioned. Implementation note: `ShapeStats.file_paths` already lists the files that contribute to a shape; cross-reference each file with its language to attribute instances. Falling back to `language_breakdown` alone is insufficient because a single category mixes files from multiple languages.
  - The existing `_catalog_pattern_entropy` and `_catalog_convention_drift` keep their behaviour unchanged. Both rollups apply the new language scoping at the category level: Python-only categories with no Python files contribute zero (they already do); shell-only categories with only Python files contribute zero. The aggregate becomes "sum across (category, language) pairs where language is in `category.languages`."
- `DivergenceSummary` (`src/sdi/snapshot/model.py:60-93`):
  - Add four new optional fields, mirroring the existing aggregates:
    - `pattern_entropy_by_language: dict[str, float] | None = None`
    - `pattern_entropy_by_language_delta: dict[str, float] | None = None`
    - `convention_drift_by_language: dict[str, float] | None = None`
    - `convention_drift_by_language_delta: dict[str, float] | None = None`
  - Update `to_dict` and `from_dict` to round-trip these fields. `from_dict` must default missing keys to `None` so older snapshots still deserialize (Non-Negotiable Rule 13).
  - Bump `SNAPSHOT_VERSION` from `"0.1.0"` to `"0.2.0"` in `src/sdi/snapshot/model.py:14`. The schema gained additive fields, so per Rule 13 trend computation against a `"0.1.0"` snapshot must warn and treat it as a baseline (no delta), not crash. Update `delta.py:_major_version` callers if needed — major version is unchanged (`0`), so existing major-version compatibility branch still applies.
- `compute_delta` (`src/sdi/snapshot/delta.py:127-196`):
  - Compute the four new per-language fields for `current`. When `previous is None`, all `_delta` fields are `None`.
  - When `previous` is present and same major version, compute deltas as `dict` differences keyed on language: any language present in either current or previous appears in the delta dict with a numeric value (defaulting to `0.0` when absent on one side). When `previous` is present but lacks the per-language fields (older `"0.1.0"` snapshot), treat as if `previous` were absent for the per-language deltas only — emit a `UserWarning` once and proceed.
- `sdi show` and `sdi diff` output (`src/sdi/cli/show_cmd.py`, `src/sdi/cli/diff_cmd.py`):
  - In text mode, render a per-language section after the existing aggregate when `pattern_entropy_by_language` is not `None`. One row per language sorted by file count (descending), with absolute and delta columns. No color thresholds; this is measurement output.
  - In `--format json` mode, the new fields appear in the output dict alongside the existing aggregate. No transformation.
- Documentation:
  - Extend `README.md`'s "what SDI measures" section with a one-paragraph note: "Pattern entropy and convention drift are reported globally and per-language. Categories declare which languages they apply to; non-applicable languages contribute zero. A 95%-shell repo's `error_handling` entropy under `pattern_entropy_by_language["shell"]` reflects shell-specific shapes only."
  - Add a `CHANGELOG.md` entry under "Unreleased": `Added: per-language pattern entropy and convention drift fields in DivergenceSummary; CategoryDefinition gains an applicable-languages field. Snapshot schema bumped to 0.2.0 (additive only).`

**Acceptance criteria:**
- Every built-in category has a non-empty `languages` field. Calling `applicable_languages(name)` for any name in `CATEGORY_NAMES` returns a non-empty `frozenset[str]`; for unknown names returns `None`.
- A snapshot of `tests/fixtures/multi-language/` (Python + TypeScript) reports `pattern_entropy_by_language` with at least two keys (`"python"` and `"typescript"`), each with non-zero entropy, and an aggregate `pattern_entropy` equal to the sum of distinct shapes across all (category, language) pairs where the language is applicable.
- A snapshot of `tests/fixtures/shell-heavy/` (M14 fixture) reports `pattern_entropy_by_language["shell"] > 0` and `pattern_entropy_by_language` has no `"python"` key (the fixture has zero Python files).
- A snapshot of a Python-only fixture reports `pattern_entropy_by_language["python"] > 0` and includes contributions from `class_hierarchy`, `context_managers`, `comprehensions` (Python-only categories) only under the `"python"` key.
- `convention_drift_by_language` partitions correctly: a Python file with a non-canonical `error_handling` shape and a shell file with a non-canonical `error_handling` shape produce two separate per-language drift values, each computed against its own canonical-per-category-per-language baseline.
- `compute_delta` against a `"0.1.0"` snapshot emits exactly one `UserWarning` per snapshot pair and returns `pattern_entropy_by_language_delta is None`. The aggregate `pattern_entropy_delta` is still computed normally.
- Snapshot round-trip: `Snapshot.from_dict(s.to_dict())` yields a `Snapshot` equal to `s` for both new and old (`"0.1.0"`) JSON inputs.
- **Determinism unchanged:** running `sdi snapshot` twice on the same fixture produces byte-identical JSON output, including the new per-language fields. Verify by hashing the serialized output in a unit test.
- **No regression on aggregate values.** For every existing fixture, the aggregate `pattern_entropy` value post-M16 must equal pre-M16 (since every category's `languages` set covers all languages that actually contribute instances on those fixtures). Capture pre-M16 aggregates in a reference snapshot and assert equality.
- `class_hierarchy`, `context_managers`, and `comprehensions` no longer contribute to non-Python languages: a fixture with a fabricated shell adapter that emits a `class_hierarchy` instance for a shell file (test-only adapter) has the instance silently dropped at catalog build time, and `pattern_entropy_by_language["shell"]` excludes it.

**Tests:**

- `tests/unit/test_categories.py` — extend (or create if absent) with:
  - one case per built-in category asserting `applicable_languages(name)` returns the expected frozenset.
  - `applicable_languages("does_not_exist")` returns `None`.
  - empty `languages` field is treated as "applies to all" — fabricate a `CategoryDefinition` with `languages=frozenset()`, register it through a private hook, verify catalog rollups include it for any language.
- `tests/unit/test_catalog.py` — extend with:
  - `build_pattern_catalog` filters out fingerprints whose category does not apply to the record's language. Use a stub fingerprint generator that emits `class_hierarchy` for a shell record; assert the resulting catalog has zero `class_hierarchy` instances.
  - `category_languages` round-trips through `to_dict` / `from_dict` with sorted lists.
- `tests/unit/test_delta.py` — extend with:
  - per-language entropy on a Python+Shell catalog: assert two keys, each with the expected count.
  - per-language drift on a Python+Shell catalog: assert two keys, each with the expected fraction.
  - delta against `previous=None`: all per-language `_delta` fields are `None`.
  - delta against a synthetic previous snapshot lacking per-language fields: emits exactly one `UserWarning`, returns per-language `_delta` as `None` while the aggregate `_delta` is computed.
  - delta with new languages added: a previous snapshot with only `python`, current with `python` + `shell`, returns a delta dict containing both keys with `previous` shell value treated as `0.0`.
- `tests/unit/test_snapshot_model.py` — extend with:
  - `DivergenceSummary` round-trips through `to_dict` / `from_dict` with all four new fields populated.
  - `Snapshot.from_dict` accepts JSON missing the new fields (a `"0.1.0"` snapshot) and produces a `Snapshot` with `pattern_entropy_by_language=None` etc.
- `tests/integration/test_full_pipeline.py` — extend the `multi-language` and `shell-heavy` cases with per-language assertions matching the acceptance criteria above.
- `tests/integration/test_cli_output.py` — assert `sdi show --format json` for a multi-language snapshot includes the per-language keys, and the text-mode output renders the per-language section.

**Watch For:**
- **Empty `languages` means "applies to all," not "applies to none."** This is a deliberate back-compat default for any future externally-defined category. Reviewers may flip the semantic to "empty means none" — that breaks the back-compat path and should be rejected. Make the convention explicit in the `CategoryDefinition` docstring.
- **`class_hierarchy`, `context_managers`, `comprehensions` are Python-only intentionally.** TS/JS classes do exist syntactically but the existing query strings target Python AST node names (`class_definition`, `with_statement`, `list_comprehension`). If a future milestone adds TS/JS queries, expand the `languages` set in *that* milestone — do not pre-emptively expand here.
- **Aggregate semantics must not change for existing inputs.** The aggregate `pattern_entropy` for a Python-only fixture must equal its pre-M16 value. The category-language scoping only excludes hypothetical fingerprints that adapters never actually emit today — it should be a no-op on existing fixture suites. The regression assertion in acceptance criteria enforces this.
- **`SNAPSHOT_VERSION` bump is additive-only.** `0.1.0` → `0.2.0` is a minor bump because the schema gained optional fields. Major version `0` is unchanged, so the existing `_major_version` compatibility branch in `delta.py` continues to allow trend computation across the bump. If `from_dict` needs to handle missing keys, do it via `.get(key)` with `None` default, never via raising.
- **Determinism: per-language dicts must be deterministically ordered when serialized.** Use sorted keys explicitly when producing `dict[str, float]` outputs so JSON round-trip is byte-stable. `json.dumps(..., sort_keys=True)` is the standard guard.
- **`async_patterns` mixing across languages is intentional and inherited from M14.** Per-language scoping does not split `async_patterns` into per-language sub-categories. A Python `async def` shape and a shell `command &` shape are different shapes (different ast_hashes) within the same category — the per-language rollup partitions *files*, not categories. Reviewers may flag the cross-language presence as a smell; it remains intentional.
- **Drift computation requires per-language canonicals.** `_catalog_convention_drift` picks one canonical hash per category. The per-language version must pick one canonical hash per (category, language) pair — otherwise a Python file is graded against a shell canonical or vice versa. This is the most common implementation mistake; add a unit case that fails if the canonical is not partitioned.
- **`languages` field is metadata, not enforcement.** The catalog filter is defensive only. The primary correctness mechanism is each adapter emitting category names that match its language's queries. The filter exists to make accidents in adapter code visible by silent zeroing, not to substitute for adapter discipline.
- **No new config key.** Per-language behaviour is unconditional — there is no `[patterns] per_language = true` flag. The aggregate still exists for back-compat consumers, and the per-language fields are always present on new snapshots. Adding a flag would create three behaviours (off / aggregate / per-language) and complicate diffing.

**Seeds Forward:**
- Makes `sdi check` thresholds amenable to per-language overrides in a future milestone (e.g., `[thresholds.overrides.error_handling.shell]`). M16 does not implement per-language thresholds — it provides the signal those thresholds would key off.
- Lays groundwork for per-language trend visualization (a future `sdi trend --by-language` flag).
- Reduces the noise in mixed-language snapshots that the validation harness in M18 must assert against.

---
