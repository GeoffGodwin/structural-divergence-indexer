"""sdi show — display details of a snapshot."""

from __future__ import annotations

from pathlib import Path

import click

from sdi.cli._helpers import (
    emit_json,
    emit_rows_csv,
    format_delta,
    load_snapshot_by_ref,
    require_initialized,
    resolve_snapshots_dir,
)
from sdi.snapshot.model import DivergenceSummary, Snapshot


def _format_text(snap: Snapshot, filename: str) -> None:
    """Print a human-readable snapshot summary to stdout.

    Args:
        snap: Snapshot to display.
        filename: Snapshot filename (for display).
    """
    div = snap.divergence
    langs = ", ".join(f"{lang}: {cnt}" for lang, cnt in snap.language_breakdown.items())
    click.echo(f"Snapshot  {filename}")
    click.echo(f"Timestamp {snap.timestamp}")
    click.echo(f"Commit    {snap.commit_sha or 'N/A'}")
    click.echo(f"Files     {snap.file_count}  ({langs or 'none'})")
    click.echo(f"Config    {snap.config_hash}")
    click.echo("")
    click.echo("Divergence Summary")
    click.echo("  {:<28} {:>10}  {:>12}".format("Dimension", "Value", "Delta"))
    click.echo("  " + "-" * 54)
    _div_row("pattern_entropy", div.pattern_entropy, div.pattern_entropy_delta)
    _div_row("convention_drift", div.convention_drift, div.convention_drift_delta)
    _div_row("coupling_topology", div.coupling_topology, div.coupling_topology_delta)
    _div_row(
        "boundary_violations",
        div.boundary_violations,
        div.boundary_violations_delta,
    )

    by_lang = div.pattern_entropy_by_language
    if by_lang:
        click.echo("")
        click.echo("Per-Language Pattern Entropy")
        click.echo("  {:<28} {:>10}  {:>12}".format("Language", "Entropy", "Delta"))
        click.echo("  " + "-" * 54)
        lang_delta = div.pattern_entropy_by_language_delta or {}
        for lang in sorted(by_lang, key=lambda n: -by_lang[n]):
            _div_row(lang, by_lang[lang], lang_delta.get(lang))

    if snap.graph_metrics:
        click.echo("")
        click.echo("Graph Metrics")
        for key, val in snap.graph_metrics.items():
            if key != "hub_nodes":
                click.echo(f"  {key:<28} {val}")
        hub_nodes = snap.graph_metrics.get("hub_nodes", [])
        if hub_nodes:
            click.echo(f"  hub_nodes                    {', '.join(hub_nodes)}")

    if snap.partition_data:
        pd = snap.partition_data
        click.echo("")
        click.echo("Community Detection")
        click.echo(f"  clusters        {pd.get('cluster_count', 'N/A')}")
        click.echo(f"  stability       {pd.get('stability_score', 'N/A')}")
        click.echo(f"  cross-boundary  {len(pd.get('inter_cluster_edges', []))} edge group(s)")

    excluded = snap.pattern_catalog.get("meta", {}).get("scope_excluded_file_count", 0)
    if excluded > 0:
        click.echo(f"Pattern catalog excluded {excluded} file(s) via patterns.scope_exclude.")


def _div_row(name: str, value: float | int | None, delta: float | int | None) -> None:
    """Print one divergence row.

    Args:
        name: Dimension name.
        value: Current absolute value.
        delta: Delta from previous snapshot.
    """
    val_str = f"{value:.4f}" if isinstance(value, float) else str(value or "N/A")
    click.echo("  {:<28} {:>10}  {:>12}".format(name, val_str, format_delta(delta)))


def _divergence_as_rows(div: DivergenceSummary) -> list[list]:
    """Return divergence as a list of CSV rows.

    Args:
        div: DivergenceSummary instance.

    Returns:
        List of [dimension, value, delta] rows.
    """
    return [
        ["pattern_entropy", div.pattern_entropy, div.pattern_entropy_delta],
        ["convention_drift", div.convention_drift, div.convention_drift_delta],
        ["coupling_topology", div.coupling_topology, div.coupling_topology_delta],
        [
            "boundary_violations",
            div.boundary_violations,
            div.boundary_violations_delta,
        ],
    ]


@click.command("show")
@click.argument("snapshot_ref", required=False, default=None)
@click.pass_context
def show_cmd(ctx: click.Context, snapshot_ref: str | None) -> None:
    """Display details of a snapshot.

    SNAPSHOT_REF may be omitted (defaults to latest), a 1-based index,
    a negative index (from latest), or a filename prefix.
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")

    snapshots_dir = resolve_snapshots_dir(repo_root, config)
    snap, path = load_snapshot_by_ref(snapshots_dir, snapshot_ref)

    if output_format == "json":
        emit_json(snap.to_dict())
    elif output_format == "csv":
        emit_rows_csv(
            ["dimension", "value", "delta"],
            _divergence_as_rows(snap.divergence),
        )
    else:
        _format_text(snap, path.name)
