# Reviewer Report — M01 Project Skeleton, Config System, and Core Data Structures

Review cycle: 2 of 4

---

## Verdict
APPROVED_WITH_NOTES

---

## Complex Blockers (senior coder)
- None

---

## Simple Blockers (jr coder)
- None

---

## Non-Blocking Notes
- Cycle-1 non-blocking note carries forward: `src/sdi/config.py:_dict_to_config` — default values are duplicated between dataclass field defaults and the `.get("key", default)` calls. Two sources of truth; annotate with a comment linking them to prevent silent divergence.
- Cycle-1 non-blocking note carries forward: `src/sdi/cli/__init__.py:24` — `ctx.obj.get("verbose", False) if ctx.obj else False` is dead code; `ctx.ensure_object(dict)` guarantees `ctx.obj` is always a dict at this point.
- Three LOW security findings from the security agent remain unaddressed (acceptable for this milestone, flagged for tracking): `SDI_CONFIG_PATH` path constraint validation (`config.py:284–285`), `SDI_SNAPSHOT_DIR` path constraint validation (`config.py:164–165`), `SDI_LOG_LEVEL` allowlist validation (`config.py:157–158`). All marked fixable by the security agent; recommend addressing in a hardening pass before first public release.
- `src/sdi/snapshot/model.py` — `from_dict`/`to_dict` docstrings are still one-liners without Args/Returns sections (CLAUDE.md requires Google-style docstrings on all public functions). Carries forward from cycle 1.

---

## Coverage Gaps
- `tests/unit/test_config.py` — No test for malformed `expires` date format (e.g. `"2026/09/30"` instead of `"2026-09-30"`). The production fix in `_validate_overrides` (lines 181–189) is correct but the happy-path inversion is untested. Add: write a config with `expires = "2026/09/30"`, assert `SystemExit(2)` and that the error message names the override.
- `src/sdi/cli/__init__.py` — global flag wiring (`--format`, `--no-color`, `--quiet`, `--verbose`), `_SDIGroup` exception-to-exit-code-1 handler, and `--version` option are still untested (carries forward from cycle 1).
- `src/sdi/cli/init_cmd.py` — `_find_git_root` walk-up logic, `_update_gitignore` idempotency, `init_cmd` happy path / `--force` / already-initialized guard / non-git-repo exit 2 are still uncovered (carries forward from cycle 1).

---

## Prior Blocker Disposition

| Blocker | Status | Evidence |
|---------|--------|----------|
| `_build_overrides` silently swallows malformed `expires` dates — should exit 2 | **FIXED** | `_validate_overrides` (lines 171–189) now calls `date.fromisoformat(entry["expires"])` in a try/except and raises `SystemExit(2)` on `ValueError`. `_build_overrides` calls `date.fromisoformat()` directly with no except clause, safe because `_validate_overrides` always runs first in `_dict_to_config` (lines 232–234). |

---

## ACP Verdicts
- ACP: FeatureRecord location (model.py vs parsing/__init__.py) — **ACCEPT** (confirmed from cycle 1; no implementation change in this cycle)
- ACP: CoreConfig gains log_level and workers fields — **ACCEPT** (confirmed from cycle 1; no implementation change in this cycle)

---

## Drift Observations
- `src/sdi/config.py:130` — `_load_toml` return type is bare `dict` with no type parameter. All private helpers use unparameterised `dict`. Will produce `disallow_any_generics` warnings if that mypy flag is ever enabled. Carries forward from cycle 1.
- `src/sdi/snapshot/__init__.py:10-11` — `write_atomic` is re-exported as a public symbol of the `sdi.snapshot` package. Its future consumers will likely import from `sdi.snapshot.storage` directly. Carries forward from cycle 1.
