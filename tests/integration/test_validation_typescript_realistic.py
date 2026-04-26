"""Validation harness for the typescript-realistic fixture (M18).

Tests that M15 (alias resolution via tsconfig.json paths), M16 (per-language
entropy), and the TypeScript adapter produce correct signal against a 16-file
TypeScript fixture simulating a small backend service.

Run condition: tree-sitter TypeScript grammar must be installed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import requires_ts_adapter, run_sdi

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
TS_FIXTURE = FIXTURES_DIR / "typescript-realistic"

# Fixture has 16 .ts files; import edges manually counted at 27.
# Floor assertions are conservative to tolerate minor fixture edits.
EXPECTED_FILE_COUNT_MIN = 15
EXPECTED_FILE_COUNT_MAX = 25
EDGE_COUNT_FLOOR = 20  # actual count: 27; see fixture README
ENTROPY_FLOOR = 5  # >= 3 error_handling + 2 logging


@pytest.fixture
def ts_realistic_project(tmp_path: Path) -> Path:
    """Copy typescript-realistic fixture into a fresh git repo."""
    shutil.copytree(TS_FIXTURE, tmp_path / "repo")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir()
    return repo


@requires_ts_adapter
def test_typescript_realistic_invariants(cli_runner, ts_realistic_project: Path) -> None:
    """Snapshot of typescript-realistic satisfies all M15/M16 invariants.

    Asserts:
    - language_breakdown["typescript"] is within 15–25 (actual: 16).
    - graph_metrics.edge_count >= 20 (actual: 27; floor is conservative).
    - graph_metrics.component_count == 1 (all files connected via src/index.ts).
    - partition_data.cluster_count >= 2 (api, db, lib form distinguishable clusters).
    - pattern_entropy_by_language["typescript"] >= 5.
    - pattern_entropy_by_language does not contain a "shell" key.
    """
    init_result = run_sdi(cli_runner, ["init"], ts_realistic_project)
    assert init_result.exit_code == 0, f"sdi init failed: {init_result.output}"

    snap_result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], ts_realistic_project)
    assert snap_result.exit_code == 0, f"sdi snapshot failed: {snap_result.output}"
    data = json.loads(snap_result.output)

    # Language breakdown
    lang_breakdown = data["language_breakdown"]
    ts_count = lang_breakdown.get("typescript", 0)
    assert EXPECTED_FILE_COUNT_MIN <= ts_count <= EXPECTED_FILE_COUNT_MAX, (
        f"language_breakdown['typescript'] = {ts_count}; expected {EXPECTED_FILE_COUNT_MIN}–{EXPECTED_FILE_COUNT_MAX}"
    )

    # Graph edge count (M15: @/* alias resolution produces edges)
    edge_count = data["graph_metrics"].get("edge_count", 0)
    assert edge_count >= EDGE_COUNT_FLOOR, (
        f"graph_metrics.edge_count = {edge_count}; expected >= {EDGE_COUNT_FLOOR}. "
        "If this fails with M15 reverted, @/* aliases are not being resolved."
    )

    # Full connectivity: all files reachable through src/index.ts
    component_count = data["graph_metrics"].get("component_count", 0)
    assert component_count == 1, (
        f"graph_metrics.component_count = {component_count}; expected 1. "
        "The fixture is designed to be fully connected through src/index.ts."
    )

    # Cluster topology: api / db / lib layers should form distinct clusters
    cluster_count = data["partition_data"].get("cluster_count", 0)
    assert cluster_count >= 2, (
        f"partition_data.cluster_count = {cluster_count}; expected >= 2. "
        "The api, db, and lib directories should form distinguishable clusters."
    )

    # Per-language entropy (M16: TypeScript patterns detected)
    by_lang = data["divergence"].get("pattern_entropy_by_language")
    assert by_lang is not None, (
        "divergence.pattern_entropy_by_language is None. "
        "If this fails with M16 reverted, the per-language field is absent."
    )
    ts_entropy = by_lang.get("typescript", -1)
    assert ts_entropy >= ENTROPY_FLOOR, (
        f"pattern_entropy_by_language['typescript'] = {ts_entropy}; "
        f"expected >= {ENTROPY_FLOOR}. "
        "The fixture has diverse try/catch and logging patterns."
    )

    # Pure-TypeScript fixture: no shell key
    assert "shell" not in by_lang, (
        f"Unexpected 'shell' key in pattern_entropy_by_language. "
        f"Keys present: {list(by_lang)}. "
        "A pure-TypeScript fixture should not produce a 'shell' key."
    )
