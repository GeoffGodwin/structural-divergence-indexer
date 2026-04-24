"""sdi boundaries — manage structural boundary specifications."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import click

from sdi.cli._helpers import (
    find_git_root,
    require_initialized,
    resolve_snapshots_dir,
)
from sdi.detection.boundaries import BoundarySpec, load_boundary_spec, partition_to_proposed_yaml
from sdi.snapshot.storage import list_snapshots, read_snapshot
from sdi.snapshot.storage import write_atomic


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _spec_as_text(spec: BoundarySpec) -> str:
    """Format a BoundarySpec as human-readable text."""
    lines = [f"Boundary Spec  version={spec.version}"]
    if spec.last_ratified:
        lines.append(f"Last ratified  {spec.last_ratified}  by {spec.ratified_by}")
    lines.append("")
    lines.append(f"Modules ({len(spec.modules)})")
    for m in spec.modules:
        layer_tag = f"  layer={m.layer}" if m.layer else ""
        lines.append(f"  {m.name}{layer_tag}")
        for p in m.paths:
            lines.append(f"    {p}")
    if spec.layers:
        lines.append("")
        order = " → ".join(spec.layers.ordering)
        lines.append(f"Layers  direction={spec.layers.direction}  ordering={order}")
    if spec.allowed_cross_domain:
        lines.append("")
        lines.append(f"Allowed cross-domain ({len(spec.allowed_cross_domain)})")
        for a in spec.allowed_cross_domain:
            lines.append(f"  {a.from_module} → {a.to}  ({a.reason})")
    if spec.aspirational_splits:
        lines.append("")
        lines.append(f"Aspirational splits ({len(spec.aspirational_splits)})")
        for s in spec.aspirational_splits:
            target = f"  target={s.target_date}" if s.target_date else ""
            lines.append(f"  {s.current_module} → {', '.join(s.intended_boundary)}{target}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sub-operations
# ---------------------------------------------------------------------------


def _do_show(spec: BoundarySpec | None, spec_path: Path) -> None:
    """Display the current ratified boundary map."""
    if spec is None:
        click.echo(
            f"No boundary spec found at {spec_path}.\n"
            "Use `sdi boundaries --propose` to generate one."
        )
        return
    click.echo(_spec_as_text(spec))


def _do_propose(repo_root: Path, config: object, spec_path: Path) -> None:
    """Show proposed boundaries from the latest snapshot's partition data."""
    from sdi.config import SDIConfig
    assert isinstance(config, SDIConfig)

    snapshots_dir = resolve_snapshots_dir(repo_root, config)
    paths = list_snapshots(snapshots_dir)
    if not paths:
        click.echo(
            "[error] No snapshots found. Run `sdi snapshot` first to generate partition data.",
            err=True,
        )
        raise SystemExit(1)

    snap = read_snapshot(paths[-1])
    pd = snap.partition_data
    if not pd or not pd.get("vertex_names"):
        click.echo(
            "[error] Latest snapshot has no partition data. Re-run `sdi snapshot`.",
            err=True,
        )
        raise SystemExit(1)

    spec = load_boundary_spec(spec_path)
    cluster_count = pd.get("cluster_count", "?")

    if spec is None:
        click.echo(
            f"No existing spec. Leiden detected {cluster_count} cluster(s) in the latest snapshot.\n"
            "Proposed starter spec (save with --export or --ratify):\n"
        )
    else:
        click.echo(
            f"Current spec has {len(spec.modules)} module(s). "
            f"Leiden detected {cluster_count} cluster(s).\n"
            "Proposed boundaries based on latest snapshot:\n"
        )

    click.echo(partition_to_proposed_yaml(pd))


def _do_ratify(spec_path: Path, partition_data: dict | None = None) -> None:
    """Open the boundary spec in $EDITOR. Writes a starter if the file is absent."""
    if not spec_path.exists():
        if partition_data:
            starter = partition_to_proposed_yaml(partition_data)
        else:
            starter = (
                "sdi_boundaries:\n"
                '  version: "0.1.0"\n'
                "  modules: []\n"
                "  allowed_cross_domain: []\n"
                "  aspirational_splits: []\n"
            )
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(spec_path, starter)
        click.echo(f"Created starter spec at {spec_path}", err=True)

    editor = os.environ.get("EDITOR")
    if not editor:
        if sys.platform.startswith("win"):
            click.echo(
                "[warning] $EDITOR is not set. Please open and edit the spec manually:\n"
                f"  {spec_path}",
                err=True,
            )
            return
        editor = "vi"

    try:
        subprocess.run([*shlex.split(editor), str(spec_path)], check=False)
    except FileNotFoundError:
        click.echo(f"[error] Editor not found: {editor!r}", err=True)
        raise SystemExit(1)


def _do_export(spec: BoundarySpec | None, export_path: Path) -> None:
    """Write the current boundary spec to a file."""
    if spec is None:
        click.echo("[error] No boundary spec to export. Create one with --ratify.", err=True)
        raise SystemExit(1)
    content = _spec_as_text(spec)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(export_path, content)
    click.echo(f"Boundary spec exported to {export_path}")


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


@click.command("boundaries")
@click.option("--propose", is_flag=True, help="Show proposed boundaries from the latest snapshot.")
@click.option("--ratify", "do_ratify", is_flag=True, help="Open boundary spec in $EDITOR.")
@click.option(
    "--export",
    "export_path",
    type=click.Path(),
    default=None,
    help="Write the boundary map to a file.",
)
@click.pass_context
def boundaries_cmd(
    ctx: click.Context,
    propose: bool,
    do_ratify: bool,
    export_path: str | None,
) -> None:
    """Manage structural boundary specifications.

    With no flags: display the current ratified boundary map.
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    spec_path = repo_root / config.boundaries.spec_file
    spec = load_boundary_spec(spec_path)

    if propose:
        _do_propose(repo_root, config, spec_path)
    elif do_ratify:
        pd = None
        snapshots_dir = resolve_snapshots_dir(repo_root, config)
        paths = list_snapshots(snapshots_dir)
        if paths:
            snap = read_snapshot(paths[-1])
            pd = snap.partition_data if snap.partition_data.get("vertex_names") else None
        _do_ratify(spec_path, partition_data=pd)
    elif export_path:
        _do_export(spec, Path(export_path))
    else:
        _do_show(spec, spec_path)
