"""M16 integration tests: per-language pattern entropy and drift in the pipeline.

Tests run against multi-language and shell-heavy fixtures.
Skipped when required tree-sitter grammars are unavailable.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import (
    requires_python_adapter,
    requires_shell_adapter,
    requires_ts_adapter,
    run_sdi,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def multilang_project(tmp_path: Path) -> Path:
    """Initialized SDI project with multi-language (Python + TypeScript) fixture."""
    fixture = FIXTURES_DIR / "multi-language"
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    for f in fixture.iterdir():
        if f.suffix in (".py", ".ts"):
            shutil.copy(f, tmp_path / f.name)
    return tmp_path


@pytest.fixture
def shell_heavy_project(tmp_path: Path) -> Path:
    """Initialized SDI project with shell-heavy fixture (pure shell, no Python)."""
    fixture = FIXTURES_DIR / "shell-heavy"
    (tmp_path / ".git").mkdir()
    sdi_dir = tmp_path / ".sdi"
    sdi_dir.mkdir()
    (sdi_dir / "snapshots").mkdir()
    for f in fixture.rglob("*.sh"):
        shutil.copy(f, tmp_path / f.name)
    return tmp_path


# ---------------------------------------------------------------------------
# Multi-language per-language tests
# ---------------------------------------------------------------------------


@requires_python_adapter
@requires_ts_adapter
class TestMultiLanguagePerLanguageFields:
    """Per-language signals on a Python+TypeScript fixture."""

    def test_pattern_entropy_by_language_has_python_and_ts(
        self, cli_runner, multilang_project
    ):
        """Snapshot of multi-language fixture includes both python and typescript keys."""
        result = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], multilang_project)
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        by_lang = data["divergence"].get("pattern_entropy_by_language")
        assert by_lang is not None, "pattern_entropy_by_language should be present"
        assert "python" in by_lang, f"Expected 'python' key; got {list(by_lang)}"
        assert "typescript" in by_lang, f"Expected 'typescript' key; got {list(by_lang)}"

    def test_snapshot_determinism_per_language(self, cli_runner, multilang_project):
        """Two snapshot runs on the same fixture produce identical per-language dicts."""
        r1 = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], multilang_project)
        r2 = run_sdi(cli_runner, ["--format", "json", "-q", "snapshot"], multilang_project)
        assert r1.exit_code == 0 and r2.exit_code == 0
        d1 = json.loads(r1.output)["divergence"].get("pattern_entropy_by_language")
        d2 = json.loads(r2.output)["divergence"].get("pattern_entropy_by_language")
        assert d1 == d2, "Per-language entropy must be deterministic across runs"


# ---------------------------------------------------------------------------
# Shell-heavy per-language tests
# ---------------------------------------------------------------------------


@requires_shell_adapter
class TestShellHeavyPerLanguageFields:
    """Per-language signals on a pure-shell fixture."""

    def test_shell_entropy_present(self, cli_runner, shell_heavy_project):
        """Shell-only project has a 'shell' key in pattern_entropy_by_language."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], shell_heavy_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        by_lang = data["divergence"].get("pattern_entropy_by_language")
        assert by_lang is not None
        assert "shell" in by_lang, f"Expected 'shell' key; got {list(by_lang or {})}"
        assert by_lang["shell"] >= 0.0

    def test_no_python_key_for_shell_only_project(self, cli_runner, shell_heavy_project):
        """A pure-shell fixture must not have a 'python' key in per-language entropy."""
        result = run_sdi(
            cli_runner, ["--format", "json", "-q", "snapshot"], shell_heavy_project
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        by_lang = data["divergence"].get("pattern_entropy_by_language") or {}
        assert "python" not in by_lang, (
            f"Shell-only fixture should have no 'python' key; got {by_lang}"
        )
