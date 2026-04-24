# Tekhton Init Report

<!-- init-report-meta
project: structural-divergence-indexer
timestamp: 2026-04-23 22:53:51
tekhton_version: 3.125.0
file_count: 146
project_type: custom
-->

## Detection Results

### Languages

| Language | Confidence | Source |
|----------|------------|--------|
| python | high | pyproject.toml |

### Frameworks

(none detected)

### Commands

| Type | Command | Source | Confidence |
|------|---------|--------|------------|
| test | `pytest` | pyproject.toml [tool.pytest] | high |
| analyze | `ruff check .` | pyproject.toml [tool.ruff] | high |

### Entry Points

(none detected)

## Config Decisions

| Key | Value | Source | Confidence |
|-----|-------|--------|------------|
| TEST_CMD | `pytest` | pyproject.toml [tool.pytest] | high |
| ANALYZE_CMD | `ruff check .` | pyproject.toml [tool.ruff] | high |

## Items Needing Review

(none — all detections look good)

## Project Summary

- **Project name:** structural-divergence-indexer
- **Project type:** custom
- **Tracked files:** 146
- **Init timestamp:** 2026-04-23 22:53:51

