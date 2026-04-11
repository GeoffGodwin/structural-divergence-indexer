"""Shared helper utilities for SDI CLI commands.

Provides:
- Git root discovery
- SDI initialization check + config loading
- Snapshot reference resolution
- Output emission helpers
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import click

from sdi.config import SDIConfig, load_config
from sdi.snapshot.model import Snapshot
from sdi.snapshot.storage import list_snapshots, read_snapshot


def find_git_root(start: Path) -> Path | None:
    """Walk up from start to find the nearest directory containing .git.

    Args:
        start: Starting directory for the upward search.

    Returns:
        Path to the git root, or None if not found.
    """
    current = start.resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def require_initialized(cwd: Path) -> tuple[Path, SDIConfig]:
    """Find git root and load SDI config, exiting on failure.

    Args:
        cwd: Starting directory for git root search.

    Returns:
        Tuple of (repo_root, config).

    Raises:
        SystemExit(2): If not in a git repo or SDI not initialized.
    """
    git_root = find_git_root(cwd)
    if git_root is None:
        click.echo("[error] Not inside a git repository.", err=True)
        raise SystemExit(2)
    if not (git_root / ".sdi").exists():
        click.echo(
            "[error] SDI not initialized. Run `sdi init` first.", err=True
        )
        raise SystemExit(2)
    config = load_config(git_root)
    return git_root, config


def resolve_snapshot_ref(snapshots_dir: Path, ref: str | None) -> Path | None:
    """Resolve a snapshot reference to a file path.

    Supports:
    - None → latest snapshot
    - Integer string → 1-based index from oldest (negative from latest)
    - Other string → filename prefix match (latest match wins)

    Args:
        snapshots_dir: Directory containing snapshots.
        ref: Reference string, or None for latest.

    Returns:
        Path to the matching snapshot file, or None if not found.
    """
    paths = list_snapshots(snapshots_dir)
    if not paths:
        return None
    if ref is None:
        return paths[-1]
    try:
        idx = int(ref)
        if idx > 0 and idx <= len(paths):
            return paths[idx - 1]
        if idx < 0 and abs(idx) <= len(paths):
            return paths[idx]
        return None
    except ValueError:
        pass
    for p in reversed(paths):
        if p.name.startswith(ref):
            return p
    return None


def load_snapshot_by_ref(
    snapshots_dir: Path, ref: str | None, label: str = "snapshot"
) -> tuple[Snapshot, Path]:
    """Load a snapshot by reference, or exit with code 1.

    Args:
        snapshots_dir: Directory containing snapshots.
        ref: Reference string (see resolve_snapshot_ref).
        label: Human-readable label for error messages.

    Returns:
        Tuple of (Snapshot, Path).

    Raises:
        SystemExit(1): If no matching snapshot is found.
    """
    path = resolve_snapshot_ref(snapshots_dir, ref)
    if path is None:
        click.echo(f"[error] No {label} found.", err=True)
        raise SystemExit(1)
    return read_snapshot(path), path


def format_delta(value: float | int | None) -> str:
    """Format a delta value with sign prefix.

    Args:
        value: Numeric delta or None.

    Returns:
        Formatted string with sign, or "N/A" for None.
    """
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:+.3f}"
    return f"{value:+d}"


def emit_rows_csv(headers: list[str], rows: list[list[Any]]) -> None:
    """Write a table as CSV to stdout.

    Args:
        headers: Column header names.
        rows: Data rows (each a list matching headers length).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    click.echo(buf.getvalue(), nl=False)


def emit_json(data: Any) -> None:
    """Write JSON-serializable data to stdout.

    Args:
        data: JSON-serializable value.
    """
    click.echo(json.dumps(data, indent=2))
