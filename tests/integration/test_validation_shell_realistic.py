"""Validation harness for the shell-heavy-realistic fixture (M18).

Tests that M15 (source resolution), M16 (per-language entropy), and M17
(scope_exclude) all produce correct signal against a 32-script shell fixture
simulating a production DevOps toolchain.

Run condition: tree-sitter Bash grammar must be installed.
Both tests are gated by requires_shell_adapter.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import requires_shell_adapter, run_sdi

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SHELL_FIXTURE = FIXTURES_DIR / "shell-heavy-realistic"

# Fixture has 32 shell files; source edges manually counted at 57.
# Floor assertions are conservative to tolerate minor fixture edits.
EXPECTED_FILE_COUNT_MIN = 30
EXPECTED_FILE_COUNT_MAX = 40
EDGE_COUNT_FLOOR = 45  # actual count: 57; see fixture README
ENTROPY_FLOOR = 15  # >= 6 error_handling + 3 data_access + 4 logging + 2 async


@pytest.fixture
def shell_realistic_project(tmp_path: Path) -> Path:
    """Copy shell-heavy-realistic fixture into a fresh git repo."""
    shutil.copytree(SHELL_FIXTURE, tmp_path / "repo")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir()
    return repo


def _take_snapshot(cli_runner, project: Path) -> dict:
    """Run sdi init + sdi snapshot; return the JSON snapshot dict."""
    init_result = run_sdi(cli_runner, ["init"], project)
    assert init_result.exit_code == 0, f"sdi init failed: {init_result.output}"

    snap_result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], project)
    assert snap_result.exit_code == 0, f"sdi snapshot failed: {snap_result.output}"
    return json.loads(snap_result.output)


def _write_scope_config(project: Path, patterns: list[str]) -> None:
    """Overwrite .sdi/config.toml with scope_exclude patterns."""
    lines = ["[patterns]", "scope_exclude = ["]
    for pat in patterns:
        lines.append(f'  "{pat}",')
    lines.append("]")
    (project / ".sdi" / "config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _clear_snapshots(project: Path) -> None:
    """Delete all snapshot files so the next run starts fresh."""
    for f in (project / ".sdi" / "snapshots").glob("*.json"):
        f.unlink()


@requires_shell_adapter
def test_shell_realistic_baseline_invariants(cli_runner, shell_realistic_project: Path) -> None:
    """Baseline snapshot of shell-heavy-realistic satisfies all M15/M16 invariants.

    Asserts:
    - language_breakdown["shell"] is within 30–40 (actual fixture count: 32).
    - graph_metrics.edge_count >= 45 (actual: 57; floor is conservative).
    - component_count <= file_count // 5 (well-connected topology).
    - partition_data.cluster_count is between 2 and file_count // 3.
    - pattern_entropy_by_language["shell"] >= 15.
    - No non-shell language key exists in pattern_entropy_by_language.
    - Python-only categories (class_hierarchy, context_managers, comprehensions)
      have zero shapes in the catalog.
    """
    data = _take_snapshot(cli_runner, shell_realistic_project)

    # Language breakdown
    lang_breakdown = data["language_breakdown"]
    shell_count = lang_breakdown.get("shell", 0)
    assert EXPECTED_FILE_COUNT_MIN <= shell_count <= EXPECTED_FILE_COUNT_MAX, (
        f"language_breakdown['shell'] = {shell_count}; expected {EXPECTED_FILE_COUNT_MIN}–{EXPECTED_FILE_COUNT_MAX}"
    )

    # Graph edge count (M15: source resolution produces edges)
    edge_count = data["graph_metrics"].get("edge_count", 0)
    assert edge_count >= EDGE_COUNT_FLOOR, (
        f"graph_metrics.edge_count = {edge_count}; expected >= {EDGE_COUNT_FLOOR}. "
        "If this fails with M15 reverted, shell sources are not being resolved."
    )

    # Connectivity: well-connected fixture should have few components
    component_count = data["graph_metrics"].get("component_count", 0)
    max_components = shell_count // 5
    assert component_count <= max_components, (
        f"graph_metrics.component_count = {component_count}; "
        f"expected <= {max_components} (file_count={shell_count} // 5)"
    )

    # Cluster topology: Leiden must find non-trivial clusters
    cluster_count = data["partition_data"].get("cluster_count", 0)
    cluster_max = shell_count // 3
    assert 2 <= cluster_count <= cluster_max, (
        f"partition_data.cluster_count = {cluster_count}; expected 2 <= count <= {cluster_max}"
    )

    # Per-language entropy (M16: shell-applicable categories detected)
    by_lang = data["divergence"].get("pattern_entropy_by_language")
    assert by_lang is not None, (
        "divergence.pattern_entropy_by_language is None. "
        "If this fails with M16 reverted, the per-language field is absent."
    )
    shell_entropy = by_lang.get("shell", -1)
    assert shell_entropy >= ENTROPY_FLOOR, (
        f"pattern_entropy_by_language['shell'] = {shell_entropy}; "
        f"expected >= {ENTROPY_FLOOR}. "
        "Indicates insufficient pattern shape diversity in the fixture."
    )

    # Pure-shell fixture: no other language keys
    for lang in by_lang:
        assert lang == "shell", (
            f"Unexpected language key in pattern_entropy_by_language: '{lang}'. "
            "A pure-shell fixture should produce only 'shell'."
        )

    # Python-only categories must have zero shapes
    catalog = data.get("pattern_catalog", {})
    python_only = ["class_hierarchy", "context_managers", "comprehensions"]
    categories = catalog.get("categories", {})
    for cat_name in python_only:
        shapes = categories.get(cat_name, {}).get("shapes", {})
        assert len(shapes) == 0, (
            f"pattern_catalog.categories.{cat_name} has {len(shapes)} shapes on a pure-shell fixture; expected 0."
        )


@requires_shell_adapter
def test_shell_realistic_with_scope_exclude(cli_runner, shell_realistic_project: Path) -> None:
    """scope_exclude=["tests/**"] reduces pattern entropy but leaves graph unchanged (M17).

    Asserts:
    - pattern_entropy_by_language["shell"] after exclusion < baseline.
    - graph_metrics.edge_count is identical to baseline.
    - graph_metrics.node_count is identical to baseline.
    - pattern_catalog.meta.scope_excluded_file_count == 5 (the five scenario files).
    """
    # Baseline snapshot
    baseline = _take_snapshot(cli_runner, shell_realistic_project)
    baseline_entropy = baseline["divergence"]["pattern_entropy_by_language"]["shell"]
    baseline_edges = baseline["graph_metrics"]["edge_count"]
    baseline_nodes = baseline["graph_metrics"]["node_count"]

    # Configure scope_exclude and take second snapshot
    _write_scope_config(shell_realistic_project, ["tests/**"])
    _clear_snapshots(shell_realistic_project)
    excluded = _take_snapshot(cli_runner, shell_realistic_project)

    # Entropy must decrease when test scenario files are excluded
    excl_entropy = excluded["divergence"]["pattern_entropy_by_language"]["shell"]
    assert excl_entropy < baseline_entropy, (
        f"pattern_entropy_by_language['shell'] with scope_exclude ({excl_entropy}) "
        f"must be < baseline ({baseline_entropy}). "
        "If this fails with M17 reverted, scope_exclude is not filtering patterns."
    )

    # Graph must be identical (scope_exclude affects patterns only, not graph)
    excl_edges = excluded["graph_metrics"]["edge_count"]
    excl_nodes = excluded["graph_metrics"]["node_count"]
    assert excl_edges == baseline_edges, (
        f"graph_metrics.edge_count changed after scope_exclude: "
        f"{baseline_edges} -> {excl_edges}. Graph must be unaffected by scope_exclude."
    )
    assert excl_nodes == baseline_nodes, (
        f"graph_metrics.node_count changed after scope_exclude: "
        f"{baseline_nodes} -> {excl_nodes}. Graph must be unaffected by scope_exclude."
    )

    # Meta block must report exactly 5 excluded files
    meta = excluded.get("pattern_catalog", {}).get("meta", {})
    excluded_count = meta.get("scope_excluded_file_count")
    assert excluded_count == 5, (
        f"pattern_catalog.meta.scope_excluded_file_count = {excluded_count}; "
        f"expected 5 (the five tests/scenario_*.sh files). "
        "If this fails with M17 reverted, the meta block is absent."
    )
