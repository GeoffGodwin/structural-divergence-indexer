"""SDI CLI — root Click group with global flags and top-level exception handler."""

from __future__ import annotations

import os
import sys
from typing import Any

import click

from sdi import __version__
from sdi.cli.init_cmd import init_cmd


class _SDIGroup(click.Group):
    """Custom group that converts unhandled exceptions to exit code 1."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except SystemExit:
            raise  # Preserve all SystemExit codes as-is
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


# ---------------------------------------------------------------------------
# Placeholder subcommands (implemented in Milestone 8)
# ---------------------------------------------------------------------------

def _not_yet_implemented(name: str) -> click.Command:
    @click.command(name)
    def _cmd(**_kwargs: Any) -> None:
        click.echo(f"sdi {name}: not yet implemented", err=True)
        raise SystemExit(1)

    _cmd.help = f"[placeholder] {name.capitalize()} — not yet implemented."
    return _cmd


for _name in ("snapshot", "diff", "trend", "check", "show", "boundaries", "catalog"):
    cli.add_command(_not_yet_implemented(_name))
