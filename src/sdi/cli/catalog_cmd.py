"""sdi catalog — display the pattern catalog from a snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from sdi.cli._helpers import (
    emit_json,
    emit_rows_csv,
    load_snapshot_by_ref,
    require_initialized,
)
from sdi.patterns import PatternCatalog


def _format_catalog_text(catalog: PatternCatalog) -> None:
    """Print a human-readable pattern catalog summary.

    Args:
        catalog: Deserialized PatternCatalog.
    """
    if not catalog.categories:
        click.echo("No pattern data in this snapshot.")
        return

    for cat_name, cat in sorted(catalog.categories.items()):
        click.echo(f"\n{cat_name}")
        click.echo(
            f"  entropy={cat.entropy}  canonical={cat.canonical_hash or 'none'}"
        )
        if not cat.shapes:
            click.echo("  (no shapes)")
            continue
        click.echo(
            "  {:<22} {:>8}  {:>8}  {:>6}  {}".format(
                "hash", "instances", "velocity", "spread", "files"
            )
        )
        click.echo("  " + "-" * 72)
        for shape in sorted(
            cat.shapes.values(), key=lambda s: -s.instance_count
        ):
            vel = "N/A" if shape.velocity is None else str(shape.velocity)
            spread = (
                "N/A" if shape.boundary_spread is None else str(shape.boundary_spread)
            )
            files_preview = ", ".join(shape.file_paths[:3])
            if len(shape.file_paths) > 3:
                files_preview += f" (+{len(shape.file_paths) - 3})"
            click.echo(
                "  {:<22} {:>8}  {:>8}  {:>6}  {}".format(
                    shape.structural_hash[:22],
                    shape.instance_count,
                    vel,
                    spread,
                    files_preview,
                )
            )


def _catalog_to_csv_rows(catalog: PatternCatalog) -> list[list[Any]]:
    """Flatten catalog to CSV rows.

    Args:
        catalog: Deserialized PatternCatalog.

    Returns:
        List of rows: [category, hash, instances, velocity, spread, files].
    """
    rows = []
    for cat_name, cat in sorted(catalog.categories.items()):
        for shape in sorted(cat.shapes.values(), key=lambda s: -s.instance_count):
            rows.append(
                [
                    cat_name,
                    shape.structural_hash,
                    shape.instance_count,
                    shape.velocity,
                    shape.boundary_spread,
                    ";".join(shape.file_paths),
                ]
            )
    return rows


@click.command("catalog")
@click.argument("snapshot_ref", required=False, default=None)
@click.pass_context
def catalog_cmd(ctx: click.Context, snapshot_ref: str | None) -> None:
    """Display the pattern catalog from a snapshot.

    SNAPSHOT_REF may be omitted (defaults to latest), a 1-based index,
    a negative index (from latest), or a filename prefix.
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")

    snapshots_dir = repo_root / config.snapshots.dir
    snap, path = load_snapshot_by_ref(snapshots_dir, snapshot_ref)

    if not snap.pattern_catalog:
        click.echo(f"[error] No pattern catalog in {path.name}.", err=True)
        raise SystemExit(1)

    catalog = PatternCatalog.from_dict(snap.pattern_catalog)

    if output_format == "json":
        emit_json({"snapshot": path.name, "catalog": snap.pattern_catalog})
    elif output_format == "csv":
        emit_rows_csv(
            ["category", "hash", "instances", "velocity", "spread", "files"],
            _catalog_to_csv_rows(catalog),
        )
    else:
        click.echo(f"Pattern Catalog — {path.name}")
        _format_catalog_text(catalog)
