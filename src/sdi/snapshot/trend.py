"""Trend computation across multiple SDI snapshots.

Extracts per-dimension time series from an ordered list of snapshots.
Snapshots are expected to be ordered chronologically (oldest first).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from sdi.snapshot.model import Snapshot

# All valid dimension names — correspond to DivergenceSummary field names.
ALL_DIMENSIONS: frozenset[str] = frozenset(
    {
        "pattern_entropy",
        "pattern_entropy_delta",
        "convention_drift",
        "convention_drift_delta",
        "coupling_topology",
        "coupling_topology_delta",
        "boundary_violations",
        "boundary_violations_delta",
    }
)


@dataclass
class TrendData:
    """Multi-snapshot trend time series for one or more SDI dimensions.

    Each dimension maps to an ordered list of values — one per snapshot.
    The first snapshot in the range always has None for delta dimensions
    (it has no previous baseline to compare against).

    Args:
        timestamps: ISO 8601 UTC timestamps of each snapshot, oldest first.
        dimensions: Mapping of dimension name to per-snapshot value series.
            Values are float or None. None indicates no measurement was available
            (first snapshot delta, or incompatible snapshot version).
    """

    timestamps: list[str]
    dimensions: dict[str, list[float | None]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return dataclasses.asdict(self)


def compute_trend(
    snapshots: list[Snapshot],
    dimensions: list[str] | None = None,
) -> TrendData:
    """Compute per-dimension trend time series from an ordered snapshot list.

    Extracts the requested dimension values from each snapshot's divergence
    summary. Handles None values (first snapshot has null deltas).

    Args:
        snapshots: Ordered list of snapshots (oldest first). May be empty.
        dimensions: Dimension names to include. If None, all eight dimensions
            are included. Unknown names are silently skipped.

    Returns:
        TrendData with one timestamp per snapshot and one value list per
        requested dimension. An empty snapshot list returns empty lists.
    """
    requested = list(dimensions) if dimensions is not None else sorted(ALL_DIMENSIONS)
    valid = [d for d in requested if d in ALL_DIMENSIONS]

    timestamps = [s.timestamp for s in snapshots]
    dim_data: dict[str, list[float | None]] = {d: [] for d in valid}

    for snap in snapshots:
        div = snap.divergence
        for dim in valid:
            raw = getattr(div, dim, None)
            if raw is None:
                dim_data[dim].append(None)
            else:
                dim_data[dim].append(float(raw))

    return TrendData(timestamps=timestamps, dimensions=dim_data)
