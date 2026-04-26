# Validation Harness

SDI includes a two-layer validation suite under `tests/integration/` that was added in M18 to close a gap exposed during dogfooding. In 2026-04, running SDI against the Tekhton shell-heavy repository produced degenerate graph topology (near-zero edges) and missing per-language entropy fields because the M15 source-resolution stage had not yet been exercised against a fixture with sufficient cross-file `source` topology, and the M16 per-language field had not been exercised against a realistic TypeScript codebase with `@/*` path aliases. The harness encodes the structural shapes observed in production as reproducible bundled fixtures, so any regression in M15, M16, or M17 produces an immediate, targeted assertion failure rather than a silent degradation.

## Layer 1: Bundled Fixtures (always runs in CI)

Two fixtures in `tests/fixtures/` are exercised on every test run:

### `tests/fixtures/shell-heavy-realistic/`

A synthetic DevOps toolchain with 32 shell scripts across `bin/`, `lib/`, `cmd/`, and `tests/`. See the [fixture README](../tests/fixtures/shell-heavy-realistic/README.md) for the manually counted edge inventory and pattern shape distribution.

**Test file:** `tests/integration/test_validation_shell_realistic.py`

| Assertion | Floor / invariant | Milestone |
|---|---|---|
| `language_breakdown["shell"]` | 30–40 | — |
| `graph_metrics.edge_count` | >= 45 | M15 (source resolution) |
| `graph_metrics.component_count` | <= file_count // 5 | M15 |
| `partition_data.cluster_count` | 2 ≤ count ≤ file_count // 3 | — |
| `pattern_entropy_by_language["shell"]` | >= 15 | M16 (per-language entropy) |
| Python-only categories have zero shapes | 0 shapes | M16 |
| `scope_excluded_file_count` with `tests/**` | == 5 | M17 (scope_exclude) |
| Entropy decreases after scope_exclude | strict decrease | M17 |
| Graph unchanged after scope_exclude | edge_count and node_count identical | M17 |

The second test in the file configures `scope_exclude = ["tests/**"]` and verifies that M17's graph-pass-through invariant holds: the five `tests/scenario_*.sh` files are excluded from pattern fingerprinting but remain in the dependency graph.

### `tests/fixtures/typescript-realistic/`

A synthetic backend service with 16 TypeScript files across `src/api/`, `src/db/`, and `src/lib/`. The `tsconfig.json` defines `@/*` path aliases targeting `src/*`, exercising the M15 alias resolver. See the [fixture README](../tests/fixtures/typescript-realistic/README.md) for the import edge inventory.

**Test file:** `tests/integration/test_validation_typescript_realistic.py`

| Assertion | Floor / invariant | Milestone |
|---|---|---|
| `language_breakdown["typescript"]` | 15–25 | — |
| `graph_metrics.edge_count` | >= 20 | M15 (alias resolution) |
| `graph_metrics.component_count` | == 1 | — |
| `partition_data.cluster_count` | >= 2 | — |
| `pattern_entropy_by_language["typescript"]` | >= 5 | M16 |
| No `"shell"` key in `pattern_entropy_by_language` | absent | M16 |

## Layer 2: Real-Repo Opt-In (never runs in default CI)

**Test file:** `tests/integration/test_validation_real_repos.py`

Two additional tests run only when specific environment variables are set:

```bash
export SDI_VALIDATION_TEKHTON=/absolute/path/to/tekhton
export SDI_VALIDATION_BIFL=/absolute/path/to/bifl-tracker
pytest tests/integration/test_validation_real_repos.py
```

**Important:** When these variables are set, `sdi init` and `sdi snapshot` will create or update `.sdi/` directories inside the target repositories. This is intentional — snapshots accumulate in the real repos for use with `sdi trend`. Users opting in should be aware their checkout will gain a `.sdi/` directory. A temp-clone approach was considered and rejected for v0: the dogfooding workflow benefits from having trend data accumulate in the real repo.

### `test_tekhton_real_repo_invariants`

Gated by `SDI_VALIDATION_TEKHTON`. Asserts:

- `graph_metrics.edge_count >= 100` (Tekhton has dozens of `lib/*.sh` files sourcing each other)
- `pattern_entropy_by_language["shell"] >= 50`
- `pattern_entropy_by_language` contains no language with zero files in `language_breakdown`

### `test_bifl_tracker_real_repo_invariants`

Gated by `SDI_VALIDATION_BIFL`. Asserts:

- `graph_metrics.edge_count >= 30`
- `pattern_entropy_by_language["typescript"] >= 10`
- If `tests/integration/fixtures/_baselines/bifl_tracker_pre_m16.json` exists: current TypeScript entropy is within 10% of the captured baseline (regression invariant). If the file is absent, the regression assertion is skipped with a warning.

### `test_real_repo_harness_skips_without_env_vars`

A meta-test that always runs and verifies that the real-repo tests skip cleanly when neither `SDI_VALIDATION_TEKHTON` nor `SDI_VALIDATION_BIFL` is set. This prevents the harness from accidentally running against arbitrary directories in CI.

## The TS Regression Baseline

The file `tests/integration/fixtures/_baselines/bifl_tracker_pre_m16.json` captures the per-language entropy values from bifl-tracker before M16 was merged. Its format:

```json
{
  "pattern_entropy_by_language": {
    "typescript": 42.0
  }
}
```

The 10% tolerance (`_BIFL_REGRESSION_TOLERANCE = 0.10`) absorbs minor structural churn. Re-capture the baseline if bifl-tracker undergoes a significant structural change:

```bash
export SDI_VALIDATION_BIFL=/path/to/bifl-tracker
cd "$SDI_VALIDATION_BIFL"
sdi init
sdi --format json -q snapshot \
  | python3 -c "
import json, sys
snap = json.load(sys.stdin)
by_lang = snap['divergence'].get('pattern_entropy_by_language', {})
print(json.dumps({'pattern_entropy_by_language': {'typescript': by_lang['typescript']}}, indent=2))
" > /path/to/sdi/tests/integration/fixtures/_baselines/bifl_tracker_pre_m16.json
```

## Updating the Bundled Fixtures

If you add or remove files or import edges in a fixture:

1. Update the README edge count table for that fixture.
2. Adjust the floor assertion constant in the corresponding test file.
3. Verify `wc -l` on all modified files stays under 300 lines.

Floor assertions are intentionally conservative (e.g., `>= 45` when actual count is 57) so that minor fixture edits do not immediately require test updates.
