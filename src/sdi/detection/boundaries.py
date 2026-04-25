"""Boundary specification parsing and intent divergence computation.

Public API:
    BoundarySpec: parsed boundary specification from .sdi/boundaries.yaml
    IntentDivergence: computed violations against a ratified spec
    load_boundary_spec(path) -> BoundarySpec | None
    compute_intent_divergence(spec, partition_data) -> IntentDivergence
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModuleSpec:
    """Module definition from the boundary spec."""

    name: str
    paths: list[str]
    layer: str | None = None


@dataclass
class LayersSpec:
    """Layer ordering and dependency direction."""

    ordering: list[str]
    direction: str = "downward"


@dataclass
class AllowedCrossDomain:
    """Declared exception for a cross-boundary dependency."""

    from_module: str
    to: str
    via: str = ""
    reason: str = ""


@dataclass
class AspirationalSplit:
    """Planned future boundary split (informational only)."""

    current_module: str
    intended_boundary: list[str]
    target_date: str = ""


@dataclass
class BoundarySpec:
    """Parsed boundary specification from .sdi/boundaries.yaml."""

    version: str
    modules: list[ModuleSpec]
    layers: LayersSpec | None = None
    allowed_cross_domain: list[AllowedCrossDomain] = field(default_factory=list)
    aspirational_splits: list[AspirationalSplit] = field(default_factory=list)
    generated_from: str = ""
    last_ratified: str = ""
    ratified_by: str = ""


@dataclass
class IntentDivergence:
    """Intent divergence computed from spec vs detected partition."""

    misplaced_files: list[str]
    unauthorized_cross_boundary: list[dict[str, Any]]
    layer_violations: list[dict[str, Any]]

    @property
    def total_violations(self) -> int:
        """Total count of all violations (files + edge groups)."""
        return len(self.misplaced_files) + len(self.unauthorized_cross_boundary) + len(self.layer_violations)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for snapshot storage."""
        return {
            "misplaced_files": self.misplaced_files,
            "unauthorized_cross_boundary": self.unauthorized_cross_boundary,
            "layer_violations": self.layer_violations,
            "total_violations": self.total_violations,
        }


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def _parse_spec(inner: dict[str, Any]) -> BoundarySpec:
    """Parse the content of the sdi_boundaries key into a BoundarySpec."""
    modules = [
        ModuleSpec(name=m["name"], paths=list(m.get("paths", [])), layer=m.get("layer"))
        for m in inner.get("modules", [])
    ]
    layers_raw = inner.get("layers")
    layers = (
        LayersSpec(
            ordering=list(layers_raw.get("ordering", [])),
            direction=layers_raw.get("direction", "downward"),
        )
        if layers_raw
        else None
    )
    allowed = [
        AllowedCrossDomain(from_module=a["from"], to=a["to"], via=a.get("via", ""), reason=a.get("reason", ""))
        for a in inner.get("allowed_cross_domain", [])
    ]
    splits = [
        AspirationalSplit(
            current_module=s["current_module"],
            intended_boundary=list(s.get("intended_boundary", [])),
            target_date=s.get("target_date", ""),
        )
        for s in inner.get("aspirational_splits", [])
    ]
    return BoundarySpec(
        version=inner["version"],
        modules=modules,
        layers=layers,
        allowed_cross_domain=allowed,
        aspirational_splits=splits,
        generated_from=inner.get("generated_from", ""),
        last_ratified=inner.get("last_ratified", ""),
        ratified_by=inner.get("ratified_by", ""),
    )


def load_boundary_spec(path: Path) -> BoundarySpec | None:
    """Parse a boundary specification YAML file.

    Returns None if the file does not exist. Exits with code 2 on parse
    errors or missing required fields, including line numbers from ruamel.yaml.

    Args:
        path: Path to the boundary spec YAML file.

    Returns:
        Parsed BoundarySpec, or None if the file is absent.
    """
    if not path.exists():
        return None
    try:
        from ruamel.yaml import YAML
    except ImportError:
        print(
            "[error] ruamel.yaml is required for boundary specs. Install: pip install ruamel.yaml",
            file=sys.stderr,
        )
        raise SystemExit(2)

    yaml = YAML(typ="rt")
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.load(fh)
    except Exception as exc:
        mark = getattr(exc, "problem_mark", None)
        line_info = f" (line {mark.line + 1})" if mark is not None else ""
        print(f"[error] {path}: malformed YAML{line_info}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if not isinstance(data, dict) or "sdi_boundaries" not in data:
        print(f"[error] {path}: missing required top-level key 'sdi_boundaries'", file=sys.stderr)
        raise SystemExit(2)

    inner = data["sdi_boundaries"]
    for required in ("version", "modules"):
        if required not in inner:
            print(
                f"[error] {path}: sdi_boundaries is missing required field '{required}'",
                file=sys.stderr,
            )
            raise SystemExit(2)

    return _parse_spec(dict(inner))


# ---------------------------------------------------------------------------
# Proposal utilities
# ---------------------------------------------------------------------------


def partition_to_proposed_yaml(partition_data: dict) -> str:
    """Generate a starter boundaries.yaml body from partition data.

    Args:
        partition_data: Partition dict from a snapshot (vertex_names, partition).

    Returns:
        YAML string suitable for writing to .sdi/boundaries.yaml.
    """
    vertex_names: list[str] = partition_data.get("vertex_names", [])
    partition: list[int] = partition_data.get("partition", [])

    cluster_files: dict[int, list[str]] = {}
    for file_path, cid in zip(vertex_names, partition):
        cluster_files.setdefault(cid, []).append(file_path)

    lines = [
        "sdi_boundaries:",
        '  version: "0.1.0"',
        '  generated_from: "leiden-community-detection"',
        "  modules:",
    ]
    for cid, files in sorted(cluster_files.items()):
        name = f"cluster_{cid}"
        lines.append(f"    - name: {name!r}")
        lines.append("      paths:")
        for f in sorted(files)[:5]:
            lines.append(f"        - {f!r}")
        if len(files) > 5:
            lines.append(f"        # ... and {len(files) - 5} more file(s)")
    lines.append("  allowed_cross_domain: []")
    lines.append("  aspirational_splits: []")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Public API (delegates to _intent module for computation)
# ---------------------------------------------------------------------------


def compute_intent_divergence(
    spec: BoundarySpec,
    partition_data: dict[str, Any],
) -> IntentDivergence:
    """Compute intent divergence between a ratified spec and a detected partition.

    Identifies three violation categories:
    - Misplaced files: in a module by path but in the wrong cluster.
    - Unauthorized cross-boundary: inter-cluster edges not in allowed_cross_domain.
    - Layer violations: dependencies that violate the declared direction.

    Args:
        spec: Ratified boundary specification.
        partition_data: Partition dict from a snapshot.

    Returns:
        IntentDivergence with all three violation lists populated.
    """
    from sdi.detection._intent import (
        _build_cluster_module_map,
        _find_layer_violations,
        _find_misplaced_files,
        _find_unauthorized_cross_boundary,
    )

    cluster_module = _build_cluster_module_map(partition_data, spec.modules)
    return IntentDivergence(
        misplaced_files=_find_misplaced_files(spec, partition_data),
        unauthorized_cross_boundary=_find_unauthorized_cross_boundary(spec, partition_data, cluster_module),
        layer_violations=_find_layer_violations(spec, partition_data, cluster_module),
    )
