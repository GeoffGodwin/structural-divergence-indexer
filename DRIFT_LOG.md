# Drift Log

## Metadata
- Last audit: never
- Runs since audit: 2

## Unresolved Observations
- [2026-04-10 | "M01"] `src/sdi/snapshot/model.py:5-6` — Comment documents that `FeatureRecord` will be re-exported from `sdi.parsing` in M02. When that happens, `tests/conftest.py`, `tests/unit/test_snapshot_model.py`, and `tests/unit/test_storage.py` all import from `sdi.snapshot.model` and will need their import lines updated.
- [2026-04-10 | "M01"] `src/sdi/config.py:_DEFAULT_EXCLUDE` — Defined as a `list` (mutable), and `CoreConfig.exclude` defaults via `field(default_factory=lambda: list(_DEFAULT_EXCLUDE))`. The extra `list()` copy in the factory is correct but the underlying `_DEFAULT_EXCLUDE` could be a `tuple` or `frozenset` to make the immutability intent clearer.

## Resolved
