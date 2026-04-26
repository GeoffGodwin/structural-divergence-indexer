"""Unit tests for sdi.config — loading, precedence, validation."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from sdi.config import (
    _DEFAULT_EXCLUDE,
    SDIConfig,
    _validate_overrides,
    load_config,
)


class TestDefaults:
    """load_config with no config files returns built-in defaults."""

    def test_returns_sdi_config(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert isinstance(cfg, SDIConfig)

    def test_default_languages(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.languages == "auto"

    def test_default_random_seed(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.random_seed == 42

    def test_default_retention(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.snapshots.retention == 100

    def test_default_leiden_gamma(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.boundaries.leiden_gamma == 1.0

    def test_default_exclude_list(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.exclude == list(_DEFAULT_EXCLUDE)

    def test_default_output_format(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.output.format == "text"

    def test_default_color(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.output.color == "auto"


class TestProjectConfigPrecedence:
    """Project-local config overrides built-in defaults."""

    def _write_config(self, directory: Path, content: str) -> None:
        sdi_dir = directory / ".sdi"
        sdi_dir.mkdir(exist_ok=True)
        (sdi_dir / "config.toml").write_text(content, encoding="utf-8")

    def test_overrides_random_seed(self, tmp_path: Path) -> None:
        self._write_config(tmp_path, "[core]\nrandom_seed = 99\n")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.random_seed == 99

    def test_overrides_retention(self, tmp_path: Path) -> None:
        self._write_config(tmp_path, "[snapshots]\nretention = 50\n")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.snapshots.retention == 50

    def test_overrides_output_format(self, tmp_path: Path) -> None:
        self._write_config(tmp_path, '[output]\nformat = "json"\n')
        cfg = load_config(project_dir=tmp_path)
        assert cfg.output.format == "json"

    def test_partial_override_preserves_defaults(self, tmp_path: Path) -> None:
        self._write_config(tmp_path, "[core]\nrandom_seed = 7\n")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.random_seed == 7
        assert cfg.snapshots.retention == 100  # untouched default


class TestExplicitConfigPath:
    """explicit config_path parameter takes precedence over project .sdi/config.toml."""

    def test_explicit_path_used(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "my_config.toml"
        cfg_file.write_text("[core]\nrandom_seed = 77\n", encoding="utf-8")
        result = load_config(config_path=cfg_file)
        assert result.core.random_seed == 77


class TestEnvVarPrecedence:
    """Environment variables override project config."""

    def test_sdi_log_level(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_LOG_LEVEL", "DEBUG")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.log_level == "DEBUG"

    def test_sdi_workers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_WORKERS", "4")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.workers == 4

    def test_sdi_snapshot_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_SNAPSHOT_DIR", "/tmp/snaps")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.snapshots.dir == "/tmp/snaps"

    def test_no_color_sets_never(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.output.color == "never"

    def test_sdi_config_path_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg_file = tmp_path / "alt.toml"
        cfg_file.write_text("[core]\nrandom_seed = 55\n", encoding="utf-8")
        monkeypatch.setenv("SDI_CONFIG_PATH", str(cfg_file))
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.random_seed == 55

    def test_env_overrides_project_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text("[core]\nworkers = 2\n", encoding="utf-8")
        monkeypatch.setenv("SDI_WORKERS", "8")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.core.workers == 8

    def test_sdi_workers_non_integer_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setenv("SDI_WORKERS", "abc")
        cfg = load_config(project_dir=tmp_path)
        # Non-integer value must be silently ignored — workers stays at default (0)
        assert cfg.core.workers == 0
        # A warning message referencing the bad value must appear on stderr
        captured = capsys.readouterr()
        assert "SDI_WORKERS" in captured.err
        assert "abc" in captured.err


class TestMalformedTOML:
    """Malformed TOML triggers SystemExit(2)."""

    def test_bad_toml_exits_2(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text("this is not valid toml [\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2

    def test_error_message_mentions_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        config_path = sdi_dir / "config.toml"
        config_path.write_text("[[invalid\n", encoding="utf-8")
        with pytest.raises(SystemExit):
            load_config(project_dir=tmp_path)
        captured = capsys.readouterr()
        assert str(config_path) in captured.err


class TestThresholdOverrides:
    """Threshold override validation — expiry is mandatory."""

    def test_missing_expires_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_overrides({"my_migration": {"reason": "no expiry here"}})
        assert exc_info.value.code == 2

    def test_invalid_date_format_exits_2(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _validate_overrides({"x": {"expires": "not-a-date"}})
        assert exc_info.value.code == 2

    def test_valid_override_passes(self) -> None:
        _validate_overrides({"x": {"expires": "2099-12-31"}})  # no exception

    def test_override_in_toml_without_expires_exits_2(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text(
            "[thresholds.overrides.my_migration]\nreason = 'no expiry'\n",
            encoding="utf-8",
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2

    def test_expired_override_silently_ignored(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text(
            '[thresholds.overrides.old_migration]\nexpires = "2000-01-01"\npattern_entropy_rate = 9.9\n',
            encoding="utf-8",
        )
        cfg = load_config(project_dir=tmp_path)
        assert "old_migration" not in cfg.thresholds.overrides

    def test_active_override_included(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text(
            '[thresholds.overrides.active]\nexpires = "2099-12-31"\npattern_entropy_rate = 9.9\n',
            encoding="utf-8",
        )
        cfg = load_config(project_dir=tmp_path)
        assert "active" in cfg.thresholds.overrides
        assert cfg.thresholds.overrides["active"].pattern_entropy_rate == 9.9


class TestUnknownKeys:
    """Unknown top-level config keys produce a DeprecationWarning."""

    def test_unknown_key_warns(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text("[deprecated_section]\nfoo = 1\n", encoding="utf-8")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_config(project_dir=tmp_path)
        assert any(
            issubclass(w.category, DeprecationWarning) and "deprecated_section" in str(w.message) for w in caught
        )


class TestScopeExclude:
    """patterns.scope_exclude config key — validation and parsing."""

    def _write_config(self, directory: Path, content: str) -> None:
        sdi_dir = directory / ".sdi"
        sdi_dir.mkdir(exist_ok=True)
        (sdi_dir / "config.toml").write_text(content, encoding="utf-8")

    def test_default_scope_exclude_is_empty(self, tmp_path: Path) -> None:
        cfg = load_config(project_dir=tmp_path)
        assert cfg.patterns.scope_exclude == []

    def test_valid_scope_exclude_parses(self, tmp_path: Path) -> None:
        self._write_config(
            tmp_path,
            '[patterns]\nscope_exclude = ["tests/**", "**/*.test.ts"]\n',
        )
        cfg = load_config(project_dir=tmp_path)
        assert cfg.patterns.scope_exclude == ["tests/**", "**/*.test.ts"]

    def test_non_string_entry_exits_2(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        self._write_config(tmp_path, "[patterns]\nscope_exclude = [42]\n")
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "non-string" in captured.err or "scope_exclude" in captured.err

    def test_empty_scope_exclude_parses(self, tmp_path: Path) -> None:
        self._write_config(tmp_path, "[patterns]\nscope_exclude = []\n")
        cfg = load_config(project_dir=tmp_path)
        assert cfg.patterns.scope_exclude == []
