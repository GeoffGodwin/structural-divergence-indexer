"""sdi snapshot — capture a structural snapshot of the repository."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from sdi.cli._helpers import (
    cache_dir,
    emit_rows_csv,
    format_delta,
    require_initialized,
    resolve_snapshots_dir,
)
from sdi.config import SDIConfig
from sdi.patterns import PatternCatalog, build_pattern_catalog
from sdi.snapshot import assemble_snapshot
from sdi.snapshot.model import Snapshot
from sdi.snapshot.storage import list_snapshots, read_snapshot


def _get_commit_sha(repo_root: Path) -> str | None:
    """Return HEAD commit SHA, or None if git is unavailable.

    Args:
        repo_root: Repository root directory.

    Returns:
        40-character hex SHA or None.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired):
        pass
    return None


def _load_previous_catalog(
    snapshots_dir: Path,
) -> PatternCatalog | None:
    """Load the pattern catalog from the most recent snapshot, if any.

    Args:
        snapshots_dir: Directory containing snapshot files.

    Returns:
        PatternCatalog from the latest snapshot, or None.
    """
    paths = list_snapshots(snapshots_dir)
    if not paths:
        return None
    snap = read_snapshot(paths[-1])
    if not snap.pattern_catalog:
        return None
    return PatternCatalog.from_dict(snap.pattern_catalog)


def _run_graph_and_detection(
    repo_root: Path,
    config: SDIConfig,
    records: list[Any],
) -> tuple[dict[str, Any], Any]:
    """Run Stages 2–3: graph construction and community detection.

    Gracefully degrades if igraph or leidenalg is not installed.

    Args:
        repo_root: Repository root.
        config: SDI configuration.
        records: Feature records from Stage 1.

    Returns:
        Tuple of (graph_metrics, community_result).
        Returns ({}, None) if igraph is unavailable.
    """
    try:
        import igraph  # noqa: F401
    except ImportError:
        click.echo(
            "[warning] igraph not installed; skipping graph analysis.", err=True
        )
        return {}, None

    from sdi.graph import build_dependency_graph, compute_graph_metrics

    graph, _ = build_dependency_graph(records, config)
    metrics = compute_graph_metrics(graph)

    try:
        import leidenalg  # noqa: F401
    except ImportError:
        click.echo(
            "[warning] leidenalg not installed; skipping community detection.",
            err=True,
        )
        return metrics, None

    from sdi.detection import detect_communities

    community = detect_communities(graph, config, cache_dir(repo_root))
    return metrics, community


def _print_snapshot_summary(snap: Snapshot, output_format: str) -> None:
    """Print a snapshot summary in the requested format.

    Args:
        snap: The captured snapshot.
        output_format: One of 'text', 'json', 'csv'.
    """
    if output_format == "json":
        click.echo(json.dumps(snap.to_dict(), indent=2))
        return

    div = snap.divergence
    if output_format == "csv":
        emit_rows_csv(
            ["dimension", "value", "delta"],
            [
                ["pattern_entropy", div.pattern_entropy, div.pattern_entropy_delta],
                ["convention_drift", div.convention_drift, div.convention_drift_delta],
                [
                    "coupling_topology",
                    div.coupling_topology,
                    div.coupling_topology_delta,
                ],
                [
                    "boundary_violations",
                    div.boundary_violations,
                    div.boundary_violations_delta,
                ],
            ],
        )
        return

    langs = ", ".join(
        f"{lang}: {cnt}" for lang, cnt in snap.language_breakdown.items()
    )
    click.echo(f"Snapshot captured at {snap.timestamp}")
    if snap.commit_sha:
        click.echo(f"  Commit    {snap.commit_sha}")
    click.echo(f"  Files     {snap.file_count}  ({langs})")
    click.echo("")
    click.echo("  Divergence:")
    pe_d = format_delta(div.pattern_entropy_delta)
    cd_d = format_delta(div.convention_drift_delta)
    ct_d = format_delta(div.coupling_topology_delta)
    bv_d = format_delta(div.boundary_violations_delta)
    click.echo(f"    pattern_entropy     {div.pattern_entropy!s:>8}  Δ {pe_d}")
    click.echo(f"    convention_drift    {div.convention_drift!s:>8}  Δ {cd_d}")
    click.echo(f"    coupling_topology   {div.coupling_topology!s:>8}  Δ {ct_d}")
    click.echo(f"    boundary_violations {div.boundary_violations!s:>8}  Δ {bv_d}")


@click.command("snapshot")
@click.pass_context
def snapshot_cmd(ctx: click.Context) -> None:
    """Capture a structural snapshot of the current repository.

    Runs the full SDI analysis pipeline:
    Stage 1: tree-sitter parsing
    Stage 2: dependency graph construction
    Stage 3: Leiden community detection
    Stage 4: pattern fingerprinting
    Stage 5: snapshot assembly and persistence
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")
    quiet = ctx.obj.get("quiet", False)

    snapshots_dir = resolve_snapshots_dir(repo_root, config)

    if not quiet:
        click.echo("Stage 1/5: Parsing source files...", err=True)

    from sdi.parsing import parse_repository
    records = parse_repository(repo_root, config)

    if not quiet:
        click.echo(f"  Parsed {len(records)} file(s).", err=True)
        click.echo("Stage 2-3/5: Graph and community detection...", err=True)

    graph_metrics, community = _run_graph_and_detection(repo_root, config, records)

    if not quiet:
        click.echo("Stage 4/5: Pattern fingerprinting...", err=True)

    prev_catalog = _load_previous_catalog(snapshots_dir)
    catalog = build_pattern_catalog(records, config, prev_catalog, community, cache_dir(repo_root))

    if not quiet:
        click.echo("Stage 5/5: Assembling snapshot...", err=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit_sha = _get_commit_sha(repo_root)

    snap = assemble_snapshot(
        records=records,
        graph_metrics=graph_metrics,
        community=community,
        catalog=catalog,
        config=config,
        commit_sha=commit_sha,
        timestamp=timestamp,
        repo_root=repo_root,
    )

    _print_snapshot_summary(snap, output_format)
