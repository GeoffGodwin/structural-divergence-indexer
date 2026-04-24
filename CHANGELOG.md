# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.9] - 2026-04-24

### Added
- [MILESTONE 13 ✓] feat: M13 (M14)
## [0.1.8] - 2026-04-24

### Added
- Milestone 13: Shell Language Discovery and Adapter Foundation. (M13)

### Added
- Added: shell language support (.sh/.bash/.zsh/.ksh and shebang detection) via tree-sitter-bash.

## [0.1.7] - 2026-04-24

### Added
- [MILESTONE 12 ✓] feat: Implement Milestone 12: Integration Tests, Polish, and Packaging

## [0.1.6] - 2026-04-24

### Added
- **`tests/fixtures/setup_fixture.py`** (NEW): Module + standalone script that creates an evolving git repository fixture with 5 commits of progressive structural drift. Exports `create_evolving_fixture(target_dir)` for use in tests. Each commit adds Python files with distinct structural patterns (single-exception handling, tuple-exception with alias and finally, async functions, multi-handler with else, logging calls). Can also be run standalone: `python setup_fixture.py [output_dir]`. (M12)
## [0.1.5] - 2026-04-24

### Added
- **`src/sdi/cli/_hooks.py`** (NEW): Git hook script templates (`POST_MERGE_MARKER`, `PRE_PUSH_MARKER`, `_POST_MERGE_BODY`, `_PRE_PUSH_BODY`) and installation utilities (`install_hook`, `install_post_merge_hook`, `install_pre_push_hook`). Non-destructive append: if the hook already contains the SDI marker it is a no-op; if it already exists without the marker, SDI block is appended; otherwise a new file with shebang is created. All hook files are made executable (u+x g+x o+x). (M11)

## [0.1.4] - 2026-04-24

### Added
- Milestone 10: Caching and Performance Optimization (M10)
## [0.1.3] - 2026-04-24

### Added
- Milestone 9: Boundary Specification and Intent Divergence (M9)

## [0.1.2] - 2026-04-23

### Added
- M08 was fully implemented in prior cycles (tester: 582 passed / 0 failed, reviewer: APPROVED_WITH_NOTES with no blockers). This cycle addressed the remaining non-blocking reviewer note: (M8)
## [0.1.1] - 2026-04-23

### Added
- Merge pull request #12 from GeoffGodwin/milestones/08 (M08)
