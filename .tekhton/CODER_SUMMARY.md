# Coder Summary
## Status: COMPLETE

## What Was Implemented

Milestone 9: Boundary Specification and Intent Divergence

1. **`src/sdi/detection/boundaries.py`** (NEW) — `BoundarySpec`, `IntentDivergence`, and supporting dataclasses (`ModuleSpec`, `LayersSpec`, `AllowedCrossDomain`, `AspirationalSplit`). Implements `load_boundary_spec()` via ruamel.yaml (round-trip, comment-preserving). Validates required fields (`version`, `modules`) and exits code 2 with line-number info on malformed YAML. `compute_intent_divergence()` delegates to `_intent.py` for computation.

2. **`src/sdi/detection/_intent.py`** (NEW) — Private helpers for intent divergence computation: `_build_cluster_module_map()`, `_find_misplaced_files()`, `_find_unauthorized_cross_boundary()`, `_find_layer_violations()`. Split from `boundaries.py` to satisfy the 300-line ceiling.

3. **`src/sdi/cli/boundaries_cmd.py`** (NEW) — `sdi boundaries` command with:
   - No flags: display current ratified boundary map (or "no spec found" message)
   - `--propose`: read latest snapshot's partition_data and display proposed cluster groupings
   - `--ratify`: open `$EDITOR` (falls back to `vi` on Unix, warns on Windows). Writes a starter spec from partition_data if no spec exists yet.
   - `--export PATH`: write current boundary map to a file

4. **`src/sdi/cli/__init__.py`** (modified) — Replaced placeholder `_not_yet_implemented("boundaries")` with real `boundaries_cmd` import and registration. Removed now-unused `Any` import (restored because it's still used in `_SDIGroup.invoke`).

5. **`src/sdi/cli/init_cmd.py`** (modified) — Added `--propose-boundaries` flag. When set, writes a starter `boundaries.yaml` from the latest snapshot's partition data (if available) or from a minimal YAML template.

6. **`src/sdi/snapshot/assembly.py`** (modified) — Added `_attach_intent_divergence()`: after building `partition_data`, loads the boundary spec and computes intent divergence, storing it in `partition_data["intent_divergence"]` if a spec exists.

7. **`src/sdi/snapshot/delta.py`** (modified) — Updated `_count_boundary_violations()` to add `intent_divergence.total_violations` to the partition-based inter-cluster edge count, implementing the "adds to, not replaces" Seeds Forward directive.

8. **`src/sdi/detection/__init__.py`** (modified) — Re-exported `BoundarySpec`, `IntentDivergence`, `load_boundary_spec`, `compute_intent_divergence` in the public API.

9. **`tests/unit/test_boundaries.py`** (NEW) — 18 tests covering: full spec parsing, missing file → None, malformed YAML → exit(2), missing required fields (parametrized), misplaced file detection, path-unmatched files not flagged, unauthorized cross-boundary detection, `allowed_cross_domain` suppression, layer violation detection, downward direction allowed, no-layers-spec skips validation, `IntentDivergence.total_violations`, `to_dict()`, empty partition data gracefully handled, ruamel.yaml comment preservation round-trip.

**Test results:** 600 passed (582 prior + 18 new), 0 failures.

## Root Cause (bugs only)
N/A — feature implementation (Milestone 9)

## Files Modified
- `src/sdi/detection/boundaries.py` — (NEW) BoundarySpec + load/parse + compute_intent_divergence
- `src/sdi/detection/_intent.py` — (NEW) private intent divergence computation helpers
- `src/sdi/detection/__init__.py` — re-exported new public API
- `src/sdi/cli/boundaries_cmd.py` — (NEW) sdi boundaries command
- `src/sdi/cli/__init__.py` — replaced placeholder with real boundaries_cmd
- `src/sdi/cli/init_cmd.py` — added --propose-boundaries flag
- `src/sdi/snapshot/assembly.py` — added _attach_intent_divergence() call
- `src/sdi/snapshot/delta.py` — updated _count_boundary_violations() to include intent divergence
- `tests/unit/test_boundaries.py` — (NEW) 18 unit tests

## Human Notes Status
No Human Notes section present in task.

## Docs Updated
None — no public-surface changes that require README/docs updates. The `sdi boundaries` command and `--propose-boundaries` flag for `sdi init` are new CLI entry points but not yet documented in README.md (which has stubs for unimplemented commands; updating is appropriate post-milestone).

## Architecture Change Proposals

### Split boundaries.py into boundaries.py + _intent.py
- **Current constraint**: CLAUDE.md says `sdi/detection/` should contain the boundary spec parsing and intent divergence computation in a single `boundaries.py` file.
- **What triggered this**: Implementation exceeded the 300-line hard ceiling before splitting.
- **Proposed change**: Public API (`BoundarySpec`, `IntentDivergence`, `load_boundary_spec`, `compute_intent_divergence`) stays in `boundaries.py`. Private computation helpers move to `_intent.py` (prefixed with `_` to signal they are not part of the public API). `compute_intent_divergence` in `boundaries.py` is a thin wrapper that delegates to `_intent.py`.
- **Backward compatible**: Yes — all public symbols remain in `boundaries.py`.
- **ARCHITECTURE.md update needed**: No — `_intent.py` is an internal implementation detail.

## Observed Issues (out of scope)
- `src/sdi/cli/init_cmd.py:174` — local `_find_git_root()` duplicates `find_git_root()` in `_helpers.py`. Pre-existing; out of scope.
- `src/sdi/cli/boundaries_cmd.py` exports a `_spec_as_text()` helper which is used for `--export`. The `--export` flag currently writes text format rather than YAML format. A future version should export YAML to preserve round-trip compatibility.
