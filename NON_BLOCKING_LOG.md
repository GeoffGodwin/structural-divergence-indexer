# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in REVIEWER_REPORT.md.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-10 | "M01"] Cycle-1 non-blocking note carries forward: `src/sdi/config.py:_dict_to_config` — default values are duplicated between dataclass field defaults and the `.get("key", default)` calls. Two sources of truth; annotate with a comment linking them to prevent silent divergence.
- [ ] [2026-04-10 | "M01"] Cycle-1 non-blocking note carries forward: `src/sdi/cli/__init__.py:24` — `ctx.obj.get("verbose", False) if ctx.obj else False` is dead code; `ctx.ensure_object(dict)` guarantees `ctx.obj` is always a dict at this point.
- [ ] [2026-04-10 | "M01"] Three LOW security findings from the security agent remain unaddressed (acceptable for this milestone, flagged for tracking): `SDI_CONFIG_PATH` path constraint validation (`config.py:284–285`), `SDI_SNAPSHOT_DIR` path constraint validation (`config.py:164–165`), `SDI_LOG_LEVEL` allowlist validation (`config.py:157–158`). All marked fixable by the security agent; recommend addressing in a hardening pass before first public release.
- [ ] [2026-04-10 | "M01"] `src/sdi/snapshot/model.py` — `from_dict`/`to_dict` docstrings are still one-liners without Args/Returns sections (CLAUDE.md requires Google-style docstrings on all public functions). Carries forward from cycle 1.
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
