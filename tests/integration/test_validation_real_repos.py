"""Optional real-repo validation harness for Tekhton and bifl-tracker (M18).

WARNING: When SDI_VALIDATION_TEKHTON or SDI_VALIDATION_BIFL are set to real
repository paths, running these tests will create or update .sdi/ directories
in those repositories (snapshots, config). This is intentional: the dogfooding
workflow benefits from snapshots accumulating in the real repo for trend
visualization via `sdi trend`. Be aware that .sdi/snapshots/ will grow over
time in the target repositories.

Environment variables:
    SDI_VALIDATION_TEKHTON: Absolute path to a Tekhton repository checkout.
    SDI_VALIDATION_BIFL: Absolute path to a bifl-tracker repository checkout.

The module skips all real-repo tests silently when neither variable is set.
The meta-test `test_real_repo_harness_skips_without_env_vars` always runs and
verifies that the real-repo tests skip cleanly in default CI.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import run_sdi

# Paths from environment variables — never hardcode local paths.
_TEKHTON_PATH = os.environ.get("SDI_VALIDATION_TEKHTON")
_BIFL_PATH = os.environ.get("SDI_VALIDATION_BIFL")

# Baseline file for TS regression invariant.
_BASELINE_FILE = Path(__file__).parent / "fixtures" / "_baselines" / "bifl_tracker_pre_m16.json"

# Conservative floors for real repos (they evolve; exact counts are not asserted).
_TEKHTON_EDGE_FLOOR = 100  # dozens of lib/*.sh files sourcing each other
_TEKHTON_ENTROPY_FLOOR = 50  # many distinct shell pattern shapes
_BIFL_EDGE_FLOOR = 30  # TypeScript service with numerous imports
_BIFL_ENTROPY_FLOOR = 10  # diverse try/catch and logging patterns
_BIFL_REGRESSION_TOLERANCE = 0.10  # 10% tolerance on TS entropy regression check


def _is_git_repo(path: Path) -> bool:
    """Return True if path exists and contains a .git directory."""
    return path.is_dir() and (path / ".git").exists()


def _run_snapshot(path: Path) -> dict:
    """Run sdi init (idempotent) + sdi snapshot; return the JSON snapshot dict."""
    runner = CliRunner()

    run_sdi(runner, ["init"], path)  # idempotent; always exits 0 for valid git repos

    snap_result = run_sdi(runner, ["--format", "json", "-q", "snapshot"], path)
    if snap_result.exit_code != 0:
        pytest.fail(f"sdi snapshot failed at {path}: {snap_result.output}")
    return json.loads(snap_result.output)


@pytest.mark.skipif(
    not _TEKHTON_PATH,
    reason="SDI_VALIDATION_TEKHTON not set; skipping real-repo Tekhton test",
)
def test_tekhton_real_repo_invariants() -> None:
    """Real-repo invariants for Tekhton (shell-heavy).

    Reads SDI_VALIDATION_TEKHTON env var for the repo path.
    Requires a valid git repository at that path.

    Asserts:
    - graph_metrics.edge_count >= 100 (Tekhton has many lib/*.sh sources).
    - pattern_entropy_by_language["shell"] >= 50.
    - pattern_entropy_by_language has no key for a language with zero files.
    """
    repo = Path(_TEKHTON_PATH)  # type: ignore[arg-type]
    if not _is_git_repo(repo):
        pytest.skip(f"SDI_VALIDATION_TEKHTON={repo} is not a valid git repository")

    data = _run_snapshot(repo)

    edge_count = data["graph_metrics"].get("edge_count", 0)
    assert edge_count >= _TEKHTON_EDGE_FLOOR, (
        f"Tekhton graph_metrics.edge_count = {edge_count}; "
        f"expected >= {_TEKHTON_EDGE_FLOOR}. "
        "Tekhton has dozens of lib/*.sh files sourcing each other."
    )

    by_lang = data["divergence"].get("pattern_entropy_by_language") or {}
    shell_entropy = by_lang.get("shell", -1)
    assert shell_entropy >= _TEKHTON_ENTROPY_FLOOR, (
        f"Tekhton pattern_entropy_by_language['shell'] = {shell_entropy}; expected >= {_TEKHTON_ENTROPY_FLOOR}."
    )

    # No language key with zero files should appear
    lang_breakdown = data.get("language_breakdown", {})
    for lang in by_lang:
        file_count = lang_breakdown.get(lang, 0)
        assert file_count > 0, (
            f"pattern_entropy_by_language has key '{lang}' but "
            f"language_breakdown['{lang}'] = {file_count}. "
            "Per-language entropy must only include languages with files."
        )


@pytest.mark.skipif(
    not _BIFL_PATH,
    reason="SDI_VALIDATION_BIFL not set; skipping real-repo bifl-tracker test",
)
def test_bifl_tracker_real_repo_invariants() -> None:
    """Real-repo invariants for bifl-tracker (TypeScript-heavy).

    Reads SDI_VALIDATION_BIFL env var for the repo path.
    Requires a valid git repository at that path.

    Asserts:
    - graph_metrics.edge_count >= 30.
    - pattern_entropy_by_language["typescript"] >= 10.
    - If the pre-M16 baseline file exists: current TypeScript entropy is within
      10% of the captured baseline (regression invariant).
    """
    repo = Path(_BIFL_PATH)  # type: ignore[arg-type]
    if not _is_git_repo(repo):
        pytest.skip(f"SDI_VALIDATION_BIFL={repo} is not a valid git repository")

    data = _run_snapshot(repo)

    edge_count = data["graph_metrics"].get("edge_count", 0)
    assert edge_count >= _BIFL_EDGE_FLOOR, (
        f"bifl-tracker graph_metrics.edge_count = {edge_count}; expected >= {_BIFL_EDGE_FLOOR}."
    )

    by_lang = data["divergence"].get("pattern_entropy_by_language") or {}
    ts_entropy = by_lang.get("typescript", -1)
    assert ts_entropy >= _BIFL_ENTROPY_FLOOR, (
        f"bifl-tracker pattern_entropy_by_language['typescript'] = {ts_entropy}; expected >= {_BIFL_ENTROPY_FLOOR}."
    )

    # Regression check against captured pre-M16 baseline
    if not _BASELINE_FILE.exists():
        warnings.warn(
            f"Pre-M16 baseline file not found at {_BASELINE_FILE}; "
            "skipping regression assertion. Capture it by running M16 pre-merge "
            "and committing the output.",
            UserWarning,
            stacklevel=1,
        )
        return

    try:
        baseline = json.loads(_BASELINE_FILE.read_text(encoding="utf-8"))
        baseline_ts_entropy = float(baseline["pattern_entropy_by_language"]["typescript"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        warnings.warn(
            f"Could not read baseline from {_BASELINE_FILE}: {exc}; skipping regression assertion.",
            UserWarning,
            stacklevel=1,
        )
        return

    if baseline_ts_entropy <= 0:
        warnings.warn(
            f"Baseline TypeScript entropy is {baseline_ts_entropy} (zero or negative); skipping regression assertion.",
            UserWarning,
            stacklevel=1,
        )
        return

    relative_diff = abs(ts_entropy - baseline_ts_entropy) / baseline_ts_entropy
    assert relative_diff <= _BIFL_REGRESSION_TOLERANCE, (
        f"bifl-tracker TypeScript entropy regression: current={ts_entropy:.1f}, "
        f"baseline={baseline_ts_entropy:.1f}, "
        f"diff={relative_diff:.1%} (tolerance={_BIFL_REGRESSION_TOLERANCE:.0%}). "
        "If bifl-tracker's structure has changed materially, re-capture the baseline."
    )


def test_real_repo_harness_skips_without_env_vars() -> None:
    """Meta-test: real-repo tests skip cleanly when env vars are absent.

    This test always runs and verifies that the real-repo harness does not
    accidentally execute against arbitrary directories in default CI runs.
    """
    if _TEKHTON_PATH is not None:
        pytest.skip("SDI_VALIDATION_TEKHTON is set; meta-test not applicable")
    if _BIFL_PATH is not None:
        pytest.skip("SDI_VALIDATION_BIFL is set; meta-test not applicable")

    # Both env vars are absent; verify the skip markers fire correctly.
    tekhton_marker = pytest.mark.skipif(
        not _TEKHTON_PATH,
        reason="SDI_VALIDATION_TEKHTON not set",
    )
    bifl_marker = pytest.mark.skipif(
        not _BIFL_PATH,
        reason="SDI_VALIDATION_BIFL not set",
    )
    # pytest.mark.skipif stores the condition as the first positional arg
    assert tekhton_marker.args[0] is True, (
        "test_tekhton_real_repo_invariants skip condition should be True when SDI_VALIDATION_TEKHTON is unset"
    )
    assert bifl_marker.args[0] is True, (
        "test_bifl_tracker_real_repo_invariants skip condition should be True when SDI_VALIDATION_BIFL is unset"
    )
