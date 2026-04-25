"""SDI CLI — root Click group with global flags and top-level exception handler."""

from __future__ import annotations

import os
import signal
import sys
from typing import Any

import click

from sdi import __version__
from sdi.cli.boundaries_cmd import boundaries_cmd
from sdi.cli.catalog_cmd import catalog_cmd
from sdi.cli.check_cmd import check_cmd
from sdi.cli.completion_cmd import completion_cmd
from sdi.cli.diff_cmd import diff_cmd
from sdi.cli.init_cmd import init_cmd
from sdi.cli.show_cmd import show_cmd
from sdi.cli.snapshot_cmd import snapshot_cmd
from sdi.cli.trend_cmd import trend_cmd


def _sigterm_handler(signum: int, frame: object) -> None:
    """Convert SIGTERM into a clean SystemExit(1) so tempfiles are cleaned up."""
    click.echo("Terminated.", err=True)
    raise SystemExit(1)


# Runs at import time — installs a SIGTERM handler so tempfile cleanup completes on kill.
signal.signal(signal.SIGTERM, _sigterm_handler)


class _SDIGroup(click.Group):
    """Custom group that converts unhandled exceptions to exit code 1."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except SystemExit:
            raise  # Preserve all SystemExit codes as-is
        except KeyboardInterrupt:
            click.echo("\nInterrupted.", err=True)
            raise SystemExit(1)
        except Exception as exc:
            verbose = ctx.obj.get("verbose", False) if ctx.obj else False
            if verbose:
                import traceback

                traceback.print_exc(file=sys.stderr)
            click.echo(f"Error: {exc}", err=True)
            raise SystemExit(1) from exc


@click.group(cls=_SDIGroup)
@click.version_option(version=__version__, prog_name="sdi")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "csv"], case_sensitive=False),
    default="text",
    help="Output format.",
)
@click.option("--no-color", is_flag=True, help="Disable colored output.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress informational output.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose/debug output.")
@click.pass_context
def cli(
    ctx: click.Context,
    output_format: str,
    no_color: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    """Structural Divergence Indexer — measure and track structural drift."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = output_format
    ctx.obj["no_color"] = no_color or bool(os.environ.get("NO_COLOR"))
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose


cli.add_command(init_cmd)
cli.add_command(snapshot_cmd)
cli.add_command(show_cmd)
cli.add_command(diff_cmd)
cli.add_command(trend_cmd)
cli.add_command(check_cmd)
cli.add_command(catalog_cmd)
cli.add_command(boundaries_cmd)
cli.add_command(completion_cmd)
