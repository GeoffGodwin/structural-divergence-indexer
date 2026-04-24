"""sdi diff — show the divergence delta between two snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from sdi.cli._helpers import (
    emit_json,
    emit_rows_csv,
    format_delta,
    require_initialized,
    resolve_snapshot_ref,
    resolve_snapshots_dir,
)
from sdi.snapshot.delta import compute_delta
from sdi.snapshot.model import DivergenceSummary, Snapshot
from sdi.snapshot.storage import list_snapshots, read_snapshot


def _load_pair(
    snapshots_dir: Path,
    ref_a: str | None,
    ref_b: str | None,
) -> tuple[Snapshot, str, Snapshot, str]:
    """Load snapshot pair for diffing.

    Defaults: A = second-to-latest, B = latest.
    If only one ref is provided, the other defaults to the latest snapshot.

    Args:
        snapshots_dir: Snapshot directory.
        ref_a: Reference for the earlier snapshot (None = second-to-latest when
            ref_b is also None, otherwise None = latest).
        ref_b: Reference for the later snapshot (None = latest).

    Returns:
        Tuple of (snap_a, name_a, snap_b, name_b).

    Raises:
        SystemExit(1): If fewer than two snapshots exist or refs don't resolve.
    """
    paths = list_snapshots(snapshots_dir)

    if ref_a is None and ref_b is None:
        # Default: last two snapshots
        if len(paths) < 2:
            click.echo("[error] Need at least 2 snapshots for diff.", err=True)
            raise SystemExit(1)
        path_a, path_b = paths[-2], paths[-1]
    else:
        # Either or both refs specified; None resolves to the latest snapshot.
        path_a_resolved = resolve_snapshot_ref(snapshots_dir, ref_a)
        path_b_resolved = resolve_snapshot_ref(snapshots_dir, ref_b)
        if path_a_resolved is None:
            click.echo(f"[error] Snapshot A not found: {ref_a!r}", err=True)
            raise SystemExit(1)
        if path_b_resolved is None:
            click.echo(f"[error] Snapshot B not found: {ref_b!r}", err=True)
            raise SystemExit(1)
        path_a, path_b = path_a_resolved, path_b_resolved

    return (
        read_snapshot(path_a),
        path_a.name,
        read_snapshot(path_b),
        path_b.name,
    )


def _print_diff_text(
    name_a: str, name_b: str, div: DivergenceSummary
) -> None:
    """Print a human-readable diff summary.

    Args:
        name_a: Earlier snapshot filename.
        name_b: Later snapshot filename.
        div: Divergence summary for snapshot B (deltas are relative to A).
    """
    click.echo(f"Diff: {name_a}  →  {name_b}")
    click.echo("")
    click.echo("  {:<28} {:>10}  {:>12}".format("Dimension", "Value (B)", "Δ (B−A)"))
    click.echo("  " + "-" * 54)

    def row(name: str, val: Any, delta: Any) -> None:
        if val is None:
            val_s = "N/A"
        elif isinstance(val, float):
            val_s = f"{val:.4f}"
        else:
            val_s = str(val)
        click.echo(
            "  {:<28} {:>10}  {:>12}".format(name, val_s, format_delta(delta))
        )

    d = div
    row("pattern_entropy", d.pattern_entropy, d.pattern_entropy_delta)
    row("convention_drift", d.convention_drift, d.convention_drift_delta)
    row("coupling_topology", d.coupling_topology, d.coupling_topology_delta)
    row("boundary_violations", d.boundary_violations, d.boundary_violations_delta)


@click.command("diff")
@click.argument("snapshot_a", required=False, default=None)
@click.argument("snapshot_b", required=False, default=None)
@click.pass_context
def diff_cmd(
    ctx: click.Context,
    snapshot_a: str | None,
    snapshot_b: str | None,
) -> None:
    """Show structural divergence delta between two snapshots.

    With no arguments, diffs the last two snapshots.
    With only SNAPSHOT_A, diffs A against the latest snapshot.
    SNAPSHOT_A and SNAPSHOT_B accept 1-based indices, negative indices,
    or filename prefixes.
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")

    snapshots_dir = resolve_snapshots_dir(repo_root, config)
    snap_a, name_a, snap_b, name_b = _load_pair(snapshots_dir, snapshot_a, snapshot_b)

    # Recompute delta of B relative to A regardless of stored values.
    divergence = compute_delta(snap_b, snap_a)

    if output_format == "json":
        emit_json(
            {
                "snapshot_a": name_a,
                "snapshot_b": name_b,
                "divergence": divergence.to_dict(),
            }
        )
    elif output_format == "csv":
        d = divergence
        emit_rows_csv(
            ["dimension", "value_b", "delta"],
            [
                ["pattern_entropy", d.pattern_entropy, d.pattern_entropy_delta],
                ["convention_drift", d.convention_drift, d.convention_drift_delta],
                ["coupling_topology", d.coupling_topology, d.coupling_topology_delta],
                [
                    "boundary_violations",
                    d.boundary_violations,
                    d.boundary_violations_delta,
                ],
            ],
        )
    else:
        _print_diff_text(name_a, name_b, divergence)
