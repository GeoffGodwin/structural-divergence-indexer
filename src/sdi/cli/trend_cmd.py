"""sdi trend — show structural divergence trends across snapshots."""

from __future__ import annotations

from pathlib import Path

import click

from sdi.cli._helpers import (
    emit_json,
    emit_rows_csv,
    require_initialized,
    resolve_snapshots_dir,
)
from sdi.snapshot import ALL_DIMENSIONS, compute_trend
from sdi.snapshot.storage import list_snapshots, read_snapshot


def _print_trend_text(
    timestamps: list[str],
    dimensions: dict[str, list],
    dim_names: list[str],
) -> None:
    """Print a tabular trend view to stdout.

    Args:
        timestamps: ISO 8601 timestamps (oldest first).
        dimensions: Mapping of dimension name to value series.
        dim_names: Ordered dimension names to display.
    """
    # Header row
    header = f"  {'Timestamp':<26}" + "".join(f"  {d[:18]:>18}" for d in dim_names)
    click.echo(header)
    click.echo("  " + "-" * (26 + 20 * len(dim_names)))

    for i, ts in enumerate(timestamps):
        row = f"  {ts:<26}"
        for dim in dim_names:
            series = dimensions.get(dim, [])
            val = series[i] if i < len(series) else None
            if val is None:
                cell = "N/A"
            elif isinstance(val, float):
                cell = f"{val:.4f}"
            else:
                cell = str(val)
            row += f"  {cell:>18}"
        click.echo(row)


@click.command("trend")
@click.option(
    "--last",
    "last_n",
    default=0,
    type=int,
    help="Include only the last N snapshots (0 = all).",
)
@click.option(
    "--dimension",
    "dimensions",
    multiple=True,
    help="Dimension to include (repeatable). Defaults to all dimensions.",
)
@click.pass_context
def trend_cmd(
    ctx: click.Context,
    last_n: int,
    dimensions: tuple[str, ...],
) -> None:
    """Show structural divergence trends across snapshots.

    Outputs time-series data for the requested dimensions.
    Use --last N to restrict to the N most recent snapshots.
    Use --dimension to select specific dimensions.

    Available dimensions:
    boundary_violations, boundary_violations_delta,
    convention_drift, convention_drift_delta,
    coupling_topology, coupling_topology_delta,
    pattern_entropy, pattern_entropy_delta
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")

    snapshots_dir = resolve_snapshots_dir(repo_root, config)
    paths = list_snapshots(snapshots_dir)

    if not paths:
        click.echo("[error] No snapshots found. Run `sdi snapshot` first.", err=True)
        raise SystemExit(1)

    if last_n > 0:
        paths = paths[-last_n:]

    snapshots = [read_snapshot(p) for p in paths]

    # Validate requested dimensions
    requested: list[str] | None = None
    if dimensions:
        invalid = [d for d in dimensions if d not in ALL_DIMENSIONS]
        if invalid:
            click.echo(
                f"[error] Unknown dimension(s): {', '.join(invalid)}. Valid: {', '.join(sorted(ALL_DIMENSIONS))}",
                err=True,
            )
            raise SystemExit(2)
        requested = list(dimensions)

    trend = compute_trend(snapshots, requested)
    dim_names = sorted(trend.dimensions.keys())

    if output_format == "json":
        emit_json(trend.to_dict())
    elif output_format == "csv":
        headers = ["timestamp"] + dim_names
        rows = []
        for i, ts in enumerate(trend.timestamps):
            row = [ts] + [trend.dimensions[d][i] if i < len(trend.dimensions.get(d, [])) else None for d in dim_names]
            rows.append(row)
        emit_rows_csv(headers, rows)
    else:
        if not trend.timestamps:
            click.echo("No trend data available.")
        else:
            _print_trend_text(trend.timestamps, trend.dimensions, dim_names)
