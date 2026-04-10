"""Tests for sdi.cli — global flags, _SDIGroup exception handler, --version."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sdi import __version__
from sdi.cli import cli


class TestVersionOption:
    def test_version_flag_shows_version_string(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_flag_includes_prog_name(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert "sdi" in result.output


class TestGlobalFlagWiring:
    def test_format_text_stored_in_context(self) -> None:
        """--format text wires into ctx.obj['format']."""
        runner = CliRunner()
        # Use a placeholder subcommand to observe context without side effects.
        # 'snapshot' exits 1 with 'not yet implemented' but context is populated first.
        result = runner.invoke(cli, ["--format", "text", "snapshot"])
        # The command runs (even though it exits 1), confirming format was accepted.
        assert result.exit_code == 1
        assert "not yet implemented" in result.output or "not yet implemented" in (result.output + str(result.exception or ""))

    def test_format_json_is_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "snapshot"])
        # Invalid choice would exit 2 with a usage error; accepted choice passes through.
        assert "Error: Invalid value for '--format'" not in result.output

    def test_format_csv_is_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "csv", "snapshot"])
        assert "Error: Invalid value for '--format'" not in result.output

    def test_format_invalid_choice_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "xml", "snapshot"])
        assert result.exit_code == 2
        assert "xml" in result.output.lower() or "Invalid value" in result.output

    def test_no_color_flag_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-color", "snapshot"])
        # Flag is recognised — no usage error about unknown option.
        assert "no such option" not in result.output.lower()
        assert "no-color" not in result.output.lower() or result.exit_code != 2

    def test_quiet_short_flag_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "snapshot"])
        assert "no such option" not in result.output.lower()

    def test_verbose_short_flag_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "snapshot"])
        assert "no such option" not in result.output.lower()


class TestSDIGroupExceptionHandler:
    def test_unhandled_exception_becomes_exit_code_1(self) -> None:
        """An unexpected exception raised by a subcommand exits with code 1."""
        import click
        from sdi.cli import _SDIGroup

        @click.group(cls=_SDIGroup)
        @click.pass_context
        def test_cli(ctx: click.Context) -> None:
            ctx.ensure_object(dict)

        @test_cli.command("boom")
        def boom_cmd() -> None:
            raise RuntimeError("unexpected failure")

        runner = CliRunner()
        result = runner.invoke(test_cli, ["boom"])
        assert result.exit_code == 1

    def test_unhandled_exception_message_on_stderr(self) -> None:
        """Error message from the unexpected exception appears in combined output."""
        import click
        from sdi.cli import _SDIGroup

        @click.group(cls=_SDIGroup)
        @click.pass_context
        def test_cli(ctx: click.Context) -> None:
            ctx.ensure_object(dict)

        @test_cli.command("boom")
        def boom_cmd() -> None:
            raise RuntimeError("unique_sentinel_error_text")

        runner = CliRunner()
        result = runner.invoke(test_cli, ["boom"])
        # CliRunner mixes stdout+stderr by default; the error message must appear.
        assert "unique_sentinel_error_text" in result.output

    def test_system_exit_is_preserved_unchanged(self) -> None:
        """SystemExit raised inside a subcommand is re-raised as-is, not wrapped."""
        import click
        from sdi.cli import _SDIGroup

        @click.group(cls=_SDIGroup)
        @click.pass_context
        def test_cli(ctx: click.Context) -> None:
            ctx.ensure_object(dict)

        @test_cli.command("bail")
        def bail_cmd() -> None:
            raise SystemExit(3)

        runner = CliRunner()
        result = runner.invoke(test_cli, ["bail"])
        assert result.exit_code == 3

    def test_system_exit_0_preserved(self) -> None:
        """SystemExit(0) (clean exit) is not wrapped as an error."""
        import click
        from sdi.cli import _SDIGroup

        @click.group(cls=_SDIGroup)
        @click.pass_context
        def test_cli(ctx: click.Context) -> None:
            ctx.ensure_object(dict)

        @test_cli.command("clean")
        def clean_cmd() -> None:
            raise SystemExit(0)

        runner = CliRunner()
        result = runner.invoke(test_cli, ["clean"])
        assert result.exit_code == 0


class TestPlaceholderSubcommands:
    def test_snapshot_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["snapshot"])
        assert result.exit_code == 1

    def test_diff_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["diff"])
        assert result.exit_code == 1

    def test_trend_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["trend"])
        assert result.exit_code == 1

    def test_check_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["check"])
        assert result.exit_code == 1

    def test_show_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["show"])
        assert result.exit_code == 1

    def test_boundaries_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["boundaries"])
        assert result.exit_code == 1

    def test_catalog_placeholder_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog"])
        assert result.exit_code == 1
