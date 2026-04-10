"""Tests for sdi.config — load_config(), precedence, validation, env vars."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from sdi.config import (
    SDIConfig,
    load_config,
)


class TestDefaults:
    def test_returns_sdi_config(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert isinstance(config, SDIConfig)

    def test_core_defaults(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.core.languages == "auto"
        assert config.core.random_seed == 42
        assert config.core.log_level == "WARNING"
        assert config.core.workers == 0

    def test_snapshots_defaults(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.snapshots.dir == ".sdi/snapshots"
        assert config.snapshots.retention == 100

    def test_boundaries_defaults(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.boundaries.leiden_gamma == 1.0
        assert config.boundaries.weighted_edges is False
        assert config.boundaries.stability_threshold == 3

    def test_thresholds_defaults(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.thresholds.pattern_entropy_rate == 2.0
        assert config.thresholds.convention_drift_rate == 3.0
        assert config.thresholds.coupling_delta_rate == 0.15
        assert config.thresholds.boundary_violation_rate == 2.0

    def test_output_defaults(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.output.format == "text"
        assert config.output.color == "auto"

    def test_no_threshold_overrides_by_default(self, tmp_path: Path) -> None:
        config = load_config(project_dir=tmp_path)
        assert config.thresholds.overrides == {}


class TestProjectConfig:
    def _sdi_dir(self, base: Path) -> Path:
        d = base / ".sdi"
        d.mkdir(exist_ok=True)
        return d

    def test_loads_project_config_file(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[snapshots]\nretention = 50\n"
        )
        config = load_config(project_dir=tmp_path)
        assert config.snapshots.retention == 50

    def test_project_overrides_defaults(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[core]\nrandom_seed = 99\n"
        )
        config = load_config(project_dir=tmp_path)
        assert config.core.random_seed == 99
        # Other defaults still apply
        assert config.snapshots.retention == 100

    def test_explicit_config_path_override(self, tmp_path: Path) -> None:
        config_file = tmp_path / "custom.toml"
        config_file.write_text("[snapshots]\nretention = 25\n")
        config = load_config(project_dir=tmp_path, config_path=config_file)
        assert config.snapshots.retention == 25

    def test_missing_sdi_dir_uses_defaults(self, tmp_path: Path) -> None:
        """No .sdi/ directory → pure defaults, no error."""
        config = load_config(project_dir=tmp_path)
        assert config.snapshots.retention == 100


class TestEnvVarOverrides:
    def test_sdi_log_level(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_LOG_LEVEL", "DEBUG")
        config = load_config(project_dir=tmp_path)
        assert config.core.log_level == "DEBUG"

    def test_sdi_workers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_WORKERS", "4")
        config = load_config(project_dir=tmp_path)
        assert config.core.workers == 4

    def test_sdi_snapshot_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDI_SNAPSHOT_DIR", "/tmp/my_snaps")
        config = load_config(project_dir=tmp_path)
        assert config.snapshots.dir == "/tmp/my_snaps"

    def test_sdi_config_path_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_file = tmp_path / "env_override.toml"
        config_file.write_text("[snapshots]\nretention = 77\n")
        monkeypatch.setenv("SDI_CONFIG_PATH", str(config_file))
        config = load_config(project_dir=tmp_path)
        assert config.snapshots.retention == 77

    def test_no_color_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NO_COLOR", "1")
        config = load_config(project_dir=tmp_path)
        assert config.output.color == "never"

    def test_sdi_config_path_arg_takes_precedence_over_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_file = tmp_path / "env.toml"
        env_file.write_text("[snapshots]\nretention = 99\n")
        arg_file = tmp_path / "arg.toml"
        arg_file.write_text("[snapshots]\nretention = 11\n")
        monkeypatch.setenv("SDI_CONFIG_PATH", str(env_file))
        config = load_config(project_dir=tmp_path, config_path=arg_file)
        assert config.snapshots.retention == 11


class TestInvalidConfig:
    def _sdi_dir(self, base: Path) -> Path:
        d = base / ".sdi"
        d.mkdir(exist_ok=True)
        return d

    def test_malformed_toml_exits_code_2(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text("[invalid\nbroken = toml here")
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2

    def test_malformed_toml_error_message_includes_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config_file = self._sdi_dir(tmp_path) / "config.toml"
        config_file.write_text("[invalid\nbroken")
        with pytest.raises(SystemExit):
            load_config(project_dir=tmp_path)
        captured = capsys.readouterr()
        assert str(config_file) in captured.err

    def test_threshold_override_missing_expires_exits_code_2(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.my_migration]\n"
            "pattern_entropy_rate = 5.0\n"
            "# expires field is deliberately absent\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2

    def test_threshold_override_missing_expires_error_names_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.missing_expiry_override]\n"
            "pattern_entropy_rate = 5.0\n"
        )
        with pytest.raises(SystemExit):
            load_config(project_dir=tmp_path)
        captured = capsys.readouterr()
        assert "missing_expiry_override" in captured.err


class TestThresholdOverrides:
    def _sdi_dir(self, base: Path) -> Path:
        d = base / ".sdi"
        d.mkdir(exist_ok=True)
        return d

    def test_expired_override_silently_ignored(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.old_migration]\n"
            'expires = "2020-01-01"\n'
            "pattern_entropy_rate = 99.0\n"
        )
        config = load_config(project_dir=tmp_path)
        assert "old_migration" not in config.thresholds.overrides

    def test_valid_future_override_applied(self, tmp_path: Path) -> None:
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.active_migration]\n"
            'expires = "2030-12-31"\n'
            "pattern_entropy_rate = 5.0\n"
            'reason = "Migrating to Result types"\n'
        )
        config = load_config(project_dir=tmp_path)
        assert "active_migration" in config.thresholds.overrides
        override = config.thresholds.overrides["active_migration"]
        assert override.pattern_entropy_rate == 5.0
        assert override.reason == "Migrating to Result types"
        assert override.expires == "2030-12-31"

    def test_override_without_rate_is_valid(self, tmp_path: Path) -> None:
        """An override with only expires + reason is valid (partial override)."""
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.partial]\n"
            'expires = "2030-01-01"\n'
            'reason = "Just a note"\n'
        )
        config = load_config(project_dir=tmp_path)
        assert "partial" in config.thresholds.overrides
        override = config.thresholds.overrides["partial"]
        assert override.pattern_entropy_rate is None


class TestMalformedExpiresDate:
    def _sdi_dir(self, base: Path) -> Path:
        d = base / ".sdi"
        d.mkdir(exist_ok=True)
        return d

    def test_malformed_expires_format_exits_code_2(self, tmp_path: Path) -> None:
        """Slash-delimited date (2026/09/30) is not ISO — must exit 2."""
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.bad_date_override]\n"
            'expires = "2026/09/30"\n'
            "pattern_entropy_rate = 5.0\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2

    def test_malformed_expires_error_message_names_the_override(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Error message must include the override name so the team knows what to fix."""
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.named_override]\n"
            'expires = "2026/09/30"\n'
            "pattern_entropy_rate = 5.0\n"
        )
        with pytest.raises(SystemExit):
            load_config(project_dir=tmp_path)
        captured = capsys.readouterr()
        assert "named_override" in captured.err

    def test_malformed_expires_plain_text_is_rejected(self, tmp_path: Path) -> None:
        """Non-date string like 'soon' must also be rejected with exit code 2."""
        (self._sdi_dir(tmp_path) / "config.toml").write_text(
            "[thresholds.overrides.typo_date]\n"
            'expires = "soon"\n'
        )
        with pytest.raises(SystemExit) as exc_info:
            load_config(project_dir=tmp_path)
        assert exc_info.value.code == 2


class TestUnknownKeys:
    def test_unknown_top_level_key_emits_deprecation_warning(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text("[unknown_section]\nfoo = \"bar\"\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_config(project_dir=tmp_path)
        messages = [str(w.message) for w in caught]
        assert any("unknown_section" in m for m in messages), (
            f"Expected DeprecationWarning about 'unknown_section', got: {messages}"
        )

    def test_known_sections_produce_no_warnings(self, tmp_path: Path) -> None:
        sdi_dir = tmp_path / ".sdi"
        sdi_dir.mkdir()
        (sdi_dir / "config.toml").write_text("[core]\nrandom_seed = 1\n")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            load_config(project_dir=tmp_path)
        assert not any(issubclass(w.category, DeprecationWarning) for w in caught)
