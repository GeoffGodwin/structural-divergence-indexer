"""sdi check — validate latest snapshot against configured thresholds.

Exit codes:
    0  All dimensions within thresholds (or null deltas on first snapshot).
    1  Runtime error.
    2  Config/environment error.
   10  One or more dimension deltas exceeded their configured threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from sdi.cli._helpers import (
    emit_json,
    emit_rows_csv,
    load_snapshot_by_ref,
    require_initialized,
)
from sdi.config import SDIConfig, ThresholdsConfig
from sdi.snapshot.model import DivergenceSummary


@dataclass
class CheckResult:
    """Result of one dimension threshold check.

    Args:
        dimension: SDI divergence dimension name (delta field).
        value: Measured delta value, or None.
        threshold: Configured maximum acceptable value.
        exceeded: True if value > threshold.
    """

    dimension: str
    value: float | int | None
    threshold: float
    exceeded: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "dimension": self.dimension,
            "value": self.value,
            "threshold": self.threshold,
            "status": "exceeded" if self.exceeded else "ok",
        }


def _effective_threshold(
    thresholds: ThresholdsConfig, key: str
) -> float:
    """Return the effective threshold for a dimension, applying active overrides.

    If any active override raises the threshold for this dimension, the
    highest value is used (most lenient override wins).

    Args:
        thresholds: Threshold configuration with overrides.
        key: Threshold key (e.g., 'pattern_entropy_rate').

    Returns:
        Effective threshold as a float.
    """
    base = getattr(thresholds, key)
    for override in thresholds.overrides.values():
        override_val = getattr(override, key, None)
        if override_val is not None:
            base = max(base, override_val)
    return base


def run_checks(div: DivergenceSummary, config: SDIConfig) -> list[CheckResult]:
    """Run all four threshold checks against a DivergenceSummary.

    Dimensions with null deltas (first snapshot) are not checked and
    do not contribute to breach status.

    Args:
        div: Divergence summary from the latest snapshot.
        config: SDI configuration with threshold settings.

    Returns:
        List of CheckResult — one per dimension.
    """
    t = config.thresholds
    checks = [
        (
            "pattern_entropy_delta",
            div.pattern_entropy_delta,
            _effective_threshold(t, "pattern_entropy_rate"),
        ),
        (
            "convention_drift_delta",
            div.convention_drift_delta,
            _effective_threshold(t, "convention_drift_rate"),
        ),
        (
            "coupling_topology_delta",
            div.coupling_topology_delta,
            _effective_threshold(t, "coupling_delta_rate"),
        ),
        (
            "boundary_violations_delta",
            div.boundary_violations_delta,
            _effective_threshold(t, "boundary_violation_rate"),
        ),
    ]
    results = []
    for dim, value, threshold in checks:
        exceeded = value is not None and value > threshold
        results.append(CheckResult(dim, value, threshold, exceeded))
    return results


def _print_check_text(results: list[CheckResult], status: str) -> None:
    """Print threshold check results as formatted text.

    Args:
        results: Per-dimension check results.
        status: Overall status string ('ok' or 'exceeded').
    """
    click.echo(f"Status: {status.upper()}")
    click.echo("")
    header = "  {:<34} {:>10}  {:>10}  {}".format(
        "Dimension", "Value", "Threshold", "Status"
    )
    click.echo(header)
    click.echo("  " + "-" * 68)
    for r in results:
        if r.value is None:
            val_s = "N/A"
        elif isinstance(r.value, float):
            val_s = f"{r.value:.4f}"
        else:
            val_s = str(r.value)
        status_s = "EXCEEDED" if r.exceeded else "ok"
        click.echo(
            "  {:<34} {:>10}  {:>10.4f}  {}".format(
                r.dimension, val_s, r.threshold, status_s
            )
        )


@click.command("check")
@click.argument("snapshot_ref", required=False, default=None)
@click.pass_context
def check_cmd(ctx: click.Context, snapshot_ref: str | None) -> None:
    """Check a snapshot against configured thresholds.

    Exits with code 10 if any dimension delta exceeds its threshold.
    Exits with code 0 if all dimensions are within thresholds.

    First-snapshot null deltas are treated as OK (no baseline to compare).

    SNAPSHOT_REF defaults to the latest snapshot.
    """
    cwd = Path.cwd()
    repo_root, config = require_initialized(cwd)
    output_format = ctx.obj.get("format", "text")

    snapshots_dir = repo_root / config.snapshots.dir
    snap, path = load_snapshot_by_ref(snapshots_dir, snapshot_ref)

    results = run_checks(snap.divergence, config)
    any_exceeded = any(r.exceeded for r in results)
    status = "exceeded" if any_exceeded else "ok"

    if output_format == "json":
        emit_json(
            {
                "snapshot": path.name,
                "status": status,
                "checks": [r.to_dict() for r in results],
            }
        )
    elif output_format == "csv":
        emit_rows_csv(
            ["dimension", "value", "threshold", "status"],
            [
                [r.dimension, r.value, r.threshold, "exceeded" if r.exceeded else "ok"]
                for r in results
            ],
        )
    else:
        _print_check_text(results, status)

    if any_exceeded:
        raise SystemExit(10)
