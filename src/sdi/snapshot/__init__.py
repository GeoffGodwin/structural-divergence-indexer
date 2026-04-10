"""Snapshot module: assembly, storage, and delta computation."""

from sdi.snapshot.model import (
    SNAPSHOT_VERSION,
    DivergenceSummary,
    FeatureRecord,
    Snapshot,
)
from sdi.snapshot.storage import (
    enforce_retention,
    list_snapshots,
    read_snapshot,
    write_atomic,
    write_snapshot,
)

__all__ = [
    "SNAPSHOT_VERSION",
    "DivergenceSummary",
    "FeatureRecord",
    "Snapshot",
    "enforce_retention",
    "list_snapshots",
    "read_snapshot",
    "write_atomic",
    "write_snapshot",
]
