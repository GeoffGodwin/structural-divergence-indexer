# Non-Blocking Notes Log

Accumulated reviewer notes that were not blocking but should be addressed.
Items are auto-collected from `## Non-Blocking Notes` in REVIEWER_REPORT.md.
The coder is prompted to address these when the count exceeds the threshold.

## Open
- [ ] [2026-04-11 | "M05"] `leiden.py:32-37,43-48`: module-level `ImportError` guard still uses `print(file=sys.stderr)` rather than `click.echo(..., err=True)`. Acceptable at import time (Click context unavailable); carry forward from cycle 1 for cleanup pass.
- [ ] [2026-04-11 | "M05"] `_partition_cache.py` `_read_cache`: exception tuple still does not include `AttributeError` or `TypeError`. A top-level JSON array parses without error but `.get()` raises `AttributeError`. Stated contract is "corrupt cache → cold start without error." Add `AttributeError, TypeError` or an `isinstance(data, dict)` guard. Carry forward from cycle 1.
- [ ] [2026-04-11 | "M05"] `_partition_cache.py` `_read_cache` return type: `dict | None` is still unparameterized — should be `dict[str, Any] | None` for mypy strictness. Minor.

(All items resolved — see Resolved section below.)
<!-- Items added here by the pipeline. Mark [x] when addressed. -->

## Resolved
