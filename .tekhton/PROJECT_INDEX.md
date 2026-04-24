# PROJECT_INDEX.md — structural-divergence-indexer

<!-- Last-Scan: 2026-04-24T02:53:50Z -->
<!-- Scan-Commit: e577c4c -->
<!-- File-Count: 146 -->
<!-- Total-Lines: 21803 -->
<!-- DOC_QUALITY_SCORE: 20 -->

**Project:** structural-divergence-indexer
**Scanned:** 2026-04-24T02:53:50Z
**Files:** 146 | **Lines:** 21803

## Directory Tree

.
./.claude
./.claude/agents
./.claude/dashboard
./.claude/dashboard/data
./.claude/index
./.claude/index/samples
./.claude/logs
./.claude/logs/archive
./.claude/logs/runs
./.claude/milestones
./.claude/watchtower_inbox
./.claude/watchtower_inbox/processed
./.mypy_cache
./.mypy_cache/3.11
./.pytest_cache
./.pytest_cache/v
./.pytest_cache/v/cache
./.ruff_cache
./.ruff_cache/0.15.10
./.tekhton
./src
./src/sdi
./src/sdi.egg-info
./src/sdi/cli
./src/sdi/detection
./src/sdi/graph
./src/sdi/parsing
./src/sdi/patterns
./src/sdi/snapshot
./tests
./tests/fixtures
./tests/fixtures/high-entropy
./tests/fixtures/multi-language
./tests/fixtures/simple-python
./tests/fixtures/simple-python/models
./tests/fixtures/simple-python/utils
./tests/integration
./tests/unit

## File Inventory

| Path | Lines | Size |
|------|------:|------|
| **.claude/dashboard/** | | |
| .claude/dashboard/app.js | 1331 | huge |

| **.claude/** | | |
| .claude/plan_answers.yaml.done | 1178 | huge |

| **./** | | |
| DESIGN.md | 1116 | huge |
| plan_answers.yaml | 1178 | huge |

| **.claude/dashboard/** | | |
| .claude/dashboard/style.css | 505 | large |

| **./** | | |
| CLAUDE.md | 629 | large |

| **tests/unit/** | | |
| tests/unit/test_assembly.py | 770 | large |

| **./** | | |
| MILESTONE_ARCHIVE.md | 397 | medium |

| **src/sdi/cli/** | | |
| src/sdi/cli/snapshot_cmd.py | 221 | medium |

| **src/sdi/** | | |
| src/sdi/config.py | 308 | medium |

| **src/sdi/detection/** | | |
| src/sdi/detection/_partition_cache.py | 207 | medium |
| src/sdi/detection/leiden.py | 238 | medium |

| **src/sdi/graph/** | | |
| src/sdi/graph/builder.py | 212 | medium |

| **src/sdi/parsing/** | | |
| src/sdi/parsing/_js_ts_common.py | 228 | medium |
| src/sdi/parsing/go.py | 238 | medium |
| src/sdi/parsing/python.py | 268 | medium |
| src/sdi/parsing/rust.py | 239 | medium |

| **src/sdi/patterns/** | | |
| src/sdi/patterns/catalog.py | 285 | medium |

| **src/sdi/snapshot/** | | |
| src/sdi/snapshot/delta.py | 217 | medium |

| **tests/integration/** | | |
| tests/integration/test_cli_output.py | 287 | medium |

| **tests/unit/** | | |
| tests/unit/test_catalog.py | 220 | medium |
| tests/unit/test_catalog_velocity_spread.py | 227 | medium |
| tests/unit/test_check_cmd.py | 212 | medium |
| tests/unit/test_config.py | 243 | medium |
| tests/unit/test_delta.py | 284 | medium |
| tests/unit/test_fingerprint.py | 365 | medium |
| tests/unit/test_go_adapter.py | 230 | medium |
| tests/unit/test_graph_builder.py | 472 | medium |
| tests/unit/test_graph_metrics.py | 298 | medium |
| tests/unit/test_java_adapter.py | 289 | medium |
| tests/unit/test_leiden.py | 236 | medium |
| tests/unit/test_leiden_internals.py | 373 | medium |
| tests/unit/test_python_adapter.py | 287 | medium |
| tests/unit/test_rust_adapter.py | 277 | medium |
| tests/unit/test_trend.py | 226 | medium |
| tests/unit/test_typescript_adapter.py | 219 | medium |

| **.claude/agents/** | | |
| .claude/agents/architect.md | 70 | small |
| .claude/agents/coder.md | 100 | small |
| .claude/agents/reviewer.md | 81 | small |
| .claude/agents/security.md | 105 | small |
| .claude/agents/tester.md | 57 | small |

| **.claude/dashboard/** | | |
| .claude/dashboard/index.html | 51 | small |

| **.claude/milestones/** | | |
| .claude/milestones/m01-project-skeleton-config-system-and-core-.md | 56 | small |
| .claude/milestones/m02-file-discovery-and-tree-sitter-parsing.md | 50 | small |
| .claude/milestones/m06-pattern-fingerprinting-and-catalog.md | 65 | small |
| .claude/milestones/m07-snapshot-assembly-delta-computation-and-.md | 53 | small |
| .claude/milestones/m08-cli-commands-snapshot-show-diff-trend-ch.md | 58 | small |

| **.claude/** | | |
| .claude/pipeline.conf | 104 | small |

| **./** | | |
| CODER_SUMMARY.md | 51 | small |
| PROJECT_INDEX.md | 148 | small |
| TEST_AUDIT_REPORT.md | 75 | small |
| plan_questions.yaml | 130 | small |
| pyproject.toml | 76 | small |

| **src/sdi/cli/** | | |
| src/sdi/cli/__init__.py | 89 | small |
| src/sdi/cli/_helpers.py | 164 | small |
| src/sdi/cli/catalog_cmd.py | 120 | small |
| src/sdi/cli/check_cmd.py | 193 | small |
| src/sdi/cli/diff_cmd.py | 151 | small |
| src/sdi/cli/init_cmd.py | 131 | small |
| src/sdi/cli/show_cmd.py | 128 | small |
| src/sdi/cli/trend_cmd.py | 128 | small |

| **src/sdi/graph/** | | |
| src/sdi/graph/metrics.py | 150 | small |

| **src/sdi/parsing/** | | |
| src/sdi/parsing/_lang_common.py | 77 | small |
| src/sdi/parsing/_python_patterns.py | 148 | small |
| src/sdi/parsing/_runner.py | 153 | small |
| src/sdi/parsing/base.py | 76 | small |
| src/sdi/parsing/discovery.py | 124 | small |
| src/sdi/parsing/java.py | 167 | small |
| src/sdi/parsing/javascript.py | 153 | small |
| src/sdi/parsing/typescript.py | 159 | small |

| **src/sdi/patterns/** | | |
| src/sdi/patterns/categories.py | 158 | small |
| src/sdi/patterns/fingerprint.py | 166 | small |

| **src/sdi/snapshot/** | | |
| src/sdi/snapshot/assembly.py | 177 | small |
| src/sdi/snapshot/model.py | 146 | small |
| src/sdi/snapshot/storage.py | 122 | small |
| src/sdi/snapshot/trend.py | 86 | small |

| **tests/** | | |
| tests/conftest.py | 186 | small |

| **tests/fixtures/simple-python/** | | |
| tests/fixtures/simple-python/service.py | 62 | small |

| **tests/fixtures/simple-python/utils/** | | |
| tests/fixtures/simple-python/utils/helpers.py | 55 | small |

| **tests/integration/** | | |
| tests/integration/test_full_pipeline.py | 175 | small |
| tests/integration/test_high_entropy_parsing.py | 189 | small |

| **tests/unit/** | | |
| tests/unit/test_categories.py | 82 | small |
| tests/unit/test_conftest_fixtures.py | 118 | small |
| tests/unit/test_discovery.py | 158 | small |
| tests/unit/test_javascript_adapter.py | 163 | small |
| tests/unit/test_snapshot_model.py | 152 | small |
| tests/unit/test_storage.py | 189 | small |

| **.claude/** | | |
| .claude/HEALTH_BASELINE.json | 14 | tiny |

| **.claude/agents/** | | |
| .claude/agents/jr-coder.md | 31 | tiny |

| **.claude/milestones/** | | |
| .claude/milestones/MANIFEST.cfg | 14 | tiny |
| .claude/milestones/m03-additional-language-adapters.md | 46 | tiny |
| .claude/milestones/m04-dependency-graph-construction-and-metric.md | 46 | tiny |
| .claude/milestones/m04-dependency-graph-construction-and-metric.md.pre-tweak | 44 | tiny |
| .claude/milestones/m05-leiden-community-detection-and-partition.md | 42 | tiny |
| .claude/milestones/m06-pattern-fingerprinting-and-catalog.md.pre-tweak | 48 | tiny |
| .claude/milestones/m09-boundary-specification-and-intent-diverg.md | 41 | tiny |
| .claude/milestones/m10-caching-and-performance-optimization.md | 35 | tiny |
| .claude/milestones/m11-git-hooks-ci-integration-and-shell-compl.md | 38 | tiny |
| .claude/milestones/m12-integration-tests-polish-and-packaging.md | 40 | tiny |

| **./** | | |
| .gitignore | 35 | tiny |
| =0.24 | 12 | tiny |
| ARCHITECTURE_LOG.md | 25 | tiny |
| DRIFT_LOG.md | 17 | tiny |
| HEALTH_REPORT.md | 24 | tiny |
| HUMAN_ACTION_REQUIRED.md | 8 | tiny |
| INIT_REPORT.md | 46 | tiny |
| NON_BLOCKING_LOG.md | 25 | tiny |
| REVIEWER_REPORT.md | 22 | tiny |
| SECURITY_NOTES.md | 6 | tiny |
| SECURITY_REPORT.md | 10 | tiny |
| TESTER_REPORT.md | 15 | tiny |

| **src/sdi/** | | |
| src/sdi/__init__.py | 3 | tiny |

| **src/sdi/detection/** | | |
| src/sdi/detection/__init__.py | 48 | tiny |

| **src/sdi/graph/** | | |
| src/sdi/graph/__init__.py | 14 | tiny |

| **src/sdi/parsing/** | | |
| src/sdi/parsing/__init__.py | 18 | tiny |

| **src/sdi/patterns/** | | |
| src/sdi/patterns/__init__.py | 30 | tiny |

| **src/sdi/snapshot/** | | |
| src/sdi/snapshot/__init__.py | 35 | tiny |

| **tests/** | | |
| tests/__init__.py | 0 | tiny |

| **tests/fixtures/high-entropy/** | | |
| tests/fixtures/high-entropy/data_cursor.py | 16 | tiny |
| tests/fixtures/high-entropy/data_dict.py | 13 | tiny |
| tests/fixtures/high-entropy/data_orm.py | 11 | tiny |
| tests/fixtures/high-entropy/error_bare.py | 10 | tiny |
| tests/fixtures/high-entropy/error_else.py | 11 | tiny |
| tests/fixtures/high-entropy/error_finally.py | 13 | tiny |
| tests/fixtures/high-entropy/error_multi.py | 10 | tiny |
| tests/fixtures/high-entropy/error_single.py | 11 | tiny |
| tests/fixtures/high-entropy/logging_instance.py | 16 | tiny |
| tests/fixtures/high-entropy/logging_module.py | 17 | tiny |
| tests/fixtures/high-entropy/mixed_patterns.py | 19 | tiny |

| **tests/fixtures/multi-language/** | | |
| tests/fixtures/multi-language/api.ts | 32 | tiny |
| tests/fixtures/multi-language/client.ts | 29 | tiny |
| tests/fixtures/multi-language/models.py | 23 | tiny |
| tests/fixtures/multi-language/models.ts | 24 | tiny |
| tests/fixtures/multi-language/service.py | 29 | tiny |
| tests/fixtures/multi-language/types.ts | 15 | tiny |
| tests/fixtures/multi-language/utils.py | 18 | tiny |

| **tests/fixtures/simple-python/** | | |
| tests/fixtures/simple-python/.gitignore | 5 | tiny |
| tests/fixtures/simple-python/__init__.py | 1 | tiny |
| tests/fixtures/simple-python/config.py | 20 | tiny |
| tests/fixtures/simple-python/main.py | 17 | tiny |

| **tests/fixtures/simple-python/models/** | | |
| tests/fixtures/simple-python/models/__init__.py | 1 | tiny |
| tests/fixtures/simple-python/models/post.py | 37 | tiny |
| tests/fixtures/simple-python/models/user.py | 37 | tiny |

| **tests/fixtures/simple-python/utils/** | | |
| tests/fixtures/simple-python/utils/__init__.py | 1 | tiny |

| **tests/integration/** | | |
| tests/integration/__init__.py | 0 | tiny |

| **tests/unit/** | | |
| tests/unit/__init__.py | 0 | tiny |

## Key Dependencies

**pyproject.toml** (pip): 6 deps, 0 dev deps
- click >=8.0
- rich >=13.0
- tomli-w >=1.0
- ruamel .yaml>=0.18
- tomli >=2.0; python_version < '3.11'
- pathspec >=0.11

## Configuration Files

| Config File | Purpose |
|-------------|---------|
| .gitignore | Git ignore rules |
| pyproject.toml | Python project configuration |
| tests/fixtures/simple-python/.gitignore | Git ignore rules |

## Test Infrastructure

**Test files:** 26
- tests/ (58 files)

## Sampled File Content

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=70"]
build-backend = "setuptools.build_meta"

[project]
name = "sdi"
version = "0.1.0"
description = "Structural Divergence Indexer — measure and track structural drift in codebases"
requires-python = ">=3.10"
license = {text = "MIT"}
readme = "README.md"
authors = [
    {name = "Geoff Godwin"},
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Quality Assurance",
]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "tomli-w>=1.0",
    "ruamel.yaml>=0.18",
    "tomli>=2.0; python_version < '3.11'",
    "pathspec>=0.11",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.3",
    "mypy>=1.0",
]
all = [
    "tree-sitter>=0.24",
    "tree-sitter-python",
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-go",
    "tree-sitter-java",
    "tree-sitter-rust",
    "leidenalg",
    "igraph",
]
web = []
systems = []

[project.scripts]
sdi = "sdi.cli:cli"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
src = ["src"]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I"]

[tool.mypy]
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = ["tomli", "leidenalg", "igraph"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### src/sdi/__init__.py

```py
"""Structural Divergence Indexer."""

__version__ = "0.1.0"
```
