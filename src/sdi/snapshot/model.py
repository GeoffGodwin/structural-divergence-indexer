"""Core data structures for SDI snapshots.

FeatureRecord is defined here as the contract between Stage 1 (parsing)
and Stages 2-4. Also re-exported as `sdi.parsing.FeatureRecord` for external callers.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Any

SNAPSHOT_VERSION = "0.1.0"


@dataclass
class FeatureRecord:
    """Per-file feature extraction result from tree-sitter parsing.

    This is the Stage 1 → Stages 2-4 contract. Every field is required.

    Args:
        file_path: Relative path to the source file from repository root.
        language: Detected language name (e.g. "python", "typescript").
        imports: List of resolved import targets (module/package names).
        symbols: List of top-level defined names (classes, functions, constants).
        pattern_instances: List of AST subtree descriptors for pattern matching.
        lines_of_code: Non-blank, non-comment line count.
        content_hash: SHA-256 hex of the file bytes at parse time. Empty string
            when deserialized from snapshots that predate M10 caching.
    """

    file_path: str
    language: str
    imports: list[str]
    symbols: list[str]
    pattern_instances: list[dict[str, Any]]
    lines_of_code: int
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe)."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureRecord":
        """Deserialize from a plain dict."""
        return cls(
            file_path=data["file_path"],
            language=data["language"],
            imports=list(data["imports"]),
            symbols=list(data["symbols"]),
            pattern_instances=list(data["pattern_instances"]),
            lines_of_code=data["lines_of_code"],
            content_hash=data.get("content_hash", ""),
        )


@dataclass
class DivergenceSummary:
    """Four-dimension structural divergence measurements for one snapshot.

    All delta fields are None on the first snapshot (no prior baseline to
    compare against). Zero means "no change between two snapshots."
    """

    pattern_entropy: float | None = None
    pattern_entropy_delta: float | None = None
    convention_drift: float | None = None
    convention_drift_delta: float | None = None
    coupling_topology: float | None = None
    coupling_topology_delta: float | None = None
    boundary_violations: int | None = None
    boundary_violations_delta: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-safe, preserves None values)."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DivergenceSummary":
        """Deserialize from a plain dict."""
        return cls(
            pattern_entropy=data.get("pattern_entropy"),
            pattern_entropy_delta=data.get("pattern_entropy_delta"),
            convention_drift=data.get("convention_drift"),
            convention_drift_delta=data.get("convention_drift_delta"),
            coupling_topology=data.get("coupling_topology"),
            coupling_topology_delta=data.get("coupling_topology_delta"),
            boundary_violations=data.get("boundary_violations"),
            boundary_violations_delta=data.get("boundary_violations_delta"),
        )


@dataclass
class Snapshot:
    """Structural snapshot capturing codebase state at one point in time.

    The snapshot_version field is mandatory and must always be present.
    Velocity fields (deltas) are None on the first snapshot.

    graph_metrics, pattern_catalog, and partition_data are stored in
    serialized dict form so that delta.compute_delta() can compare
    two snapshots without re-running the pipeline.
    """

    snapshot_version: str
    timestamp: str  # ISO 8601 UTC, e.g. "2026-04-10T17:25:00Z"
    commit_sha: str | None
    config_hash: str
    divergence: DivergenceSummary
    file_count: int
    language_breakdown: dict[str, int]
    feature_records: list[FeatureRecord] = field(default_factory=list)
    graph_metrics: dict[str, Any] = field(default_factory=dict)
    pattern_catalog: dict[str, Any] = field(default_factory=dict)
    partition_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict. Uses dataclasses.asdict for deep nesting."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        """Deserialize from a plain dict (as produced by to_dict or parsed JSON)."""
        return cls(
            snapshot_version=data["snapshot_version"],
            timestamp=data["timestamp"],
            commit_sha=data.get("commit_sha"),
            config_hash=data["config_hash"],
            divergence=DivergenceSummary.from_dict(data["divergence"]),
            file_count=data["file_count"],
            language_breakdown=dict(data["language_breakdown"]),
            feature_records=[FeatureRecord.from_dict(fr) for fr in data.get("feature_records", [])],
            graph_metrics=dict(data.get("graph_metrics", {})),
            pattern_catalog=dict(data.get("pattern_catalog", {})),
            partition_data=dict(data.get("partition_data", {})),
        )

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Snapshot":
        """Deserialize from a JSON string."""
        return cls.from_dict(json.loads(json_str))
