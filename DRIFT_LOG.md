# Drift Log

## Metadata
- Last audit: never
- Runs since audit: 1

## Unresolved Observations
- [2026-04-10 | "M01"] `src/sdi/config.py:130` — `_load_toml` return type is bare `dict` with no type parameter. All private helpers use unparameterised `dict`. Will produce `disallow_any_generics` warnings if that mypy flag is ever enabled. Carries forward from cycle 1.
- [2026-04-10 | "M01"] `src/sdi/snapshot/__init__.py:10-11` — `write_atomic` is re-exported as a public symbol of the `sdi.snapshot` package. Its future consumers will likely import from `sdi.snapshot.storage` directly. Carries forward from cycle 1.

## Resolved
