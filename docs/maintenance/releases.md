# Release Process

How a release is cut, validated, published, and recorded.

## Pipeline stages

The `release.yml` workflow runs on every `v*` tag push. Stages are sequential — failure stops the chain.

1. **validate** — confirms the git tag matches `pyproject.toml` `[project].version`. Catches the most common release-time mistake.
2. **gate** — runs the full lint + typecheck + test matrix (Python 3.10/3.11/3.12) against the tagged commit.
3. **build** — builds sdist and wheel via `python -m build`, then validates with `twine check`.
4. **release** — creates a GitHub Release, attaches the dist artifacts, and uses the matching `CHANGELOG.md` section as the release body.

PyPI publishing is intentionally omitted until SDI exits the battle-test phase. When ready, a publish job will be added that uses PyPI Trusted Publishing (OIDC) — no long-lived tokens.

## Cutting a release

For a normal MILESTONE or PATCH release on `main`:

```bash
# 1. Update pyproject.toml version
# 2. Promote [Unreleased] section in CHANGELOG.md to [X.M.P] - YYYY-MM-DD
# 3. Commit
git commit -m "release: vX.M.P"

# 4. Tag and push
git tag vX.M.P
git push origin main --tags
```

The push of the tag triggers `release.yml`. Validate stage will fail loudly if the tag does not match `pyproject.toml`.

## Pre-release tags

Tags containing `-rc`, `-beta`, or `-alpha` (e.g., `v1.0.0-rc.1`) are auto-marked as pre-release in the GitHub Release. The release pipeline runs the same validation; only the visibility flag differs.

## Tag protection

Tags should be created from `main` after CI is green. Force-pushing a tag that already triggered a release is destructive — the GitHub Release exists with old artifacts, and force-pushing creates a divergence. Re-cut with a fresh patch number instead.

## CHANGELOG hygiene

The release pipeline extracts the section heading `## [X.M.P] - YYYY-MM-DD` from `CHANGELOG.md` to populate the GitHub Release body. If no matching section exists, a generic message is used — but that is a sign you forgot to promote `[Unreleased]`.

Every release entry should follow Keep a Changelog structure:

```
## [X.M.P] - YYYY-MM-DD

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
```

Sections with no entries are omitted.

## Version single-sourcing

`pyproject.toml` is the single authoritative version declaration. `src/sdi/__init__.py` reads from package metadata via `importlib.metadata`. After bumping `pyproject.toml`, run `pip install -e .` once locally to refresh the metadata cache; CI does this fresh on every run.

## See also

- [Versioning](versioning.md) — the version-number scheme.
- [DESIGN_v1.md §12](../design/v1.md) — full versioning and release policy spec.
