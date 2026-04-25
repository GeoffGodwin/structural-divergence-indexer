"""Unit tests for sdi.detection.boundaries — BoundarySpec parsing and intent divergence."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from sdi.detection.boundaries import (
    AllowedCrossDomain,
    AspirationalSplit,
    BoundarySpec,
    IntentDivergence,
    LayersSpec,
    ModuleSpec,
    compute_intent_divergence,
    load_boundary_spec,
)

# Helpers


def _yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "boundaries.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


_FULL_YAML = """\
    sdi_boundaries:
      version: "0.1.0"
      generated_from: "leiden-community-detection"
      last_ratified: "2026-04-01T00:00:00Z"
      ratified_by: "alice"
      modules:
        - name: billing
          paths: [src/billing/, src/invoicing/]
          layer: domain
        - name: users
          paths: [src/users/]
          layer: domain
        - name: web
          paths: [src/web/]
          layer: presentation
      layers:
        ordering: [presentation, domain, infrastructure]
        direction: downward
      allowed_cross_domain:
        - from: billing
          to: users
          reason: Billing needs user account status
      aspirational_splits:
        - current_module: billing
          intended_boundary: [billing_core, invoicing]
          target_date: "2026-Q3"
"""


def _spec(
    *,
    modules: list[ModuleSpec] | None = None,
    layers: LayersSpec | None = None,
    allowed: list[AllowedCrossDomain] | None = None,
) -> BoundarySpec:
    return BoundarySpec(version="0.1.0", modules=modules or [], layers=layers, allowed_cross_domain=allowed or [])


def _pd(files: list[str], clusters: list[int], edges: list[dict] | None = None) -> dict:
    return {
        "partition": clusters,
        "vertex_names": files,
        "inter_cluster_edges": edges or [],
        "cluster_count": len(set(clusters)),
        "stability_score": 1.0,
    }


_LAYERS = LayersSpec(ordering=["presentation", "domain", "infrastructure"], direction="downward")

# Parsing tests


def test_parse_valid_spec(tmp_path: Path) -> None:
    """All fields of a full boundary spec are parsed correctly."""
    spec = load_boundary_spec(_yaml(tmp_path, _FULL_YAML))
    assert spec is not None
    assert spec.version == "0.1.0"
    assert spec.ratified_by == "alice"
    billing = next(m for m in spec.modules if m.name == "billing")
    assert billing.paths == ["src/billing/", "src/invoicing/"]
    assert billing.layer == "domain"
    assert spec.layers is not None
    assert spec.layers.ordering == ["presentation", "domain", "infrastructure"]
    assert spec.layers.direction == "downward"
    assert len(spec.allowed_cross_domain) == 1
    assert spec.allowed_cross_domain[0].from_module == "billing"
    assert len(spec.aspirational_splits) == 1
    s = spec.aspirational_splits[0]
    assert isinstance(s, AspirationalSplit)
    assert s.current_module == "billing"
    assert "billing_core" in s.intended_boundary
    assert s.target_date == "2026-Q3"


def test_missing_spec_file_returns_none(tmp_path: Path) -> None:
    """load_boundary_spec returns None when the file is absent — not an error."""
    assert load_boundary_spec(tmp_path / "nonexistent.yaml") is None


def test_malformed_yaml_exits_code_2(tmp_path: Path) -> None:
    path = tmp_path / "boundaries.yaml"
    path.write_text("sdi_boundaries:\n  version: [\n  bad", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        load_boundary_spec(path)
    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    "yaml_text",
    [
        "sdi_boundaries:\n  modules: []\n",  # missing version
        'sdi_boundaries:\n  version: "0.1.0"\n',  # missing modules
        "version: 0.1.0\nmodules: []\n",  # missing sdi_boundaries root key
    ],
)
def test_missing_required_fields_exit_code_2(tmp_path: Path, yaml_text: str) -> None:
    """Missing version, modules, or sdi_boundaries root key each exit with code 2."""
    with pytest.raises(SystemExit) as exc_info:
        load_boundary_spec(_yaml(tmp_path, yaml_text))
    assert exc_info.value.code == 2


def test_minimal_valid_spec(tmp_path: Path) -> None:
    spec = load_boundary_spec(_yaml(tmp_path, 'sdi_boundaries:\n  version: "0.1.0"\n  modules: []\n'))
    assert spec is not None and spec.modules == [] and spec.layers is None and spec.aspirational_splits == []


# Misplaced files


def test_misplaced_file_detected() -> None:
    """A file in a module's path but in the wrong cluster is flagged as misplaced."""
    spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"])])
    partition = _pd(["src/billing/a.py", "src/billing/b.py", "src/billing/c.py"], [0, 0, 1])
    result = compute_intent_divergence(spec, partition)
    assert "src/billing/c.py" in result.misplaced_files
    assert "src/billing/a.py" not in result.misplaced_files


def test_files_not_matching_module_not_flagged() -> None:
    """Files not matching any module path are not flagged as misplaced."""
    spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"])])
    result = compute_intent_divergence(spec, _pd(["src/billing/a.py", "src/other/x.py"], [0, 1]))
    assert "src/other/x.py" not in result.misplaced_files


# Unauthorized cross-boundary


def test_unauthorized_cross_boundary_detected() -> None:
    """An inter-cluster edge between modules not in allowed_cross_domain is flagged."""
    spec = _spec(
        modules=[
            ModuleSpec(name="billing", paths=["src/billing/"]),
            ModuleSpec(name="users", paths=["src/users/"]),
        ]
    )
    partition = _pd(
        ["src/billing/a.py", "src/users/u.py"],
        [0, 1],
        edges=[{"source_cluster": 0, "target_cluster": 1, "count": 3}],
    )
    result = compute_intent_divergence(spec, partition)
    assert len(result.unauthorized_cross_boundary) == 1
    assert result.unauthorized_cross_boundary[0]["from_module"] == "billing"
    assert result.unauthorized_cross_boundary[0]["to_module"] == "users"


def test_allowed_cross_domain_suppresses_flag() -> None:
    """A cross-boundary edge listed in allowed_cross_domain is not flagged."""
    spec = _spec(
        modules=[
            ModuleSpec(name="billing", paths=["src/billing/"]),
            ModuleSpec(name="users", paths=["src/users/"]),
        ],
        allowed=[AllowedCrossDomain(from_module="billing", to="users")],
    )
    partition = _pd(
        ["src/billing/a.py", "src/users/u.py"],
        [0, 1],
        edges=[{"source_cluster": 0, "target_cluster": 1, "count": 3}],
    )
    assert compute_intent_divergence(spec, partition).unauthorized_cross_boundary == []


# Layer violations


def test_layer_violation_detected_upward_dependency() -> None:
    """domain → presentation is a violation in downward architecture."""
    spec = _spec(
        modules=[
            ModuleSpec(name="web", paths=["src/web/"], layer="presentation"),
            ModuleSpec(name="billing", paths=["src/billing/"], layer="domain"),
        ],
        layers=_LAYERS,
    )
    partition = _pd(
        ["src/billing/a.py", "src/web/w.py"],
        [0, 1],
        edges=[{"source_cluster": 0, "target_cluster": 1, "count": 2}],
    )
    result = compute_intent_divergence(spec, partition)
    assert len(result.layer_violations) == 1
    v = result.layer_violations[0]
    assert v["from_module"] == "billing" and v["to_module"] == "web"
    assert v["from_layer"] == "domain" and v["to_layer"] == "presentation"


def test_downward_dependency_not_a_violation() -> None:
    """presentation → domain is allowed in downward architecture."""
    spec = _spec(
        modules=[
            ModuleSpec(name="web", paths=["src/web/"], layer="presentation"),
            ModuleSpec(name="billing", paths=["src/billing/"], layer="domain"),
        ],
        layers=_LAYERS,
        allowed=[AllowedCrossDomain(from_module="web", to="billing")],
    )
    partition = _pd(
        ["src/web/w.py", "src/billing/a.py"],
        [0, 1],
        edges=[{"source_cluster": 0, "target_cluster": 1, "count": 2}],
    )
    assert compute_intent_divergence(spec, partition).layer_violations == []


def test_no_layers_spec_skips_layer_validation() -> None:
    """Layer validation is skipped when no layers section is defined."""
    spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"], layer="domain")])
    partition = _pd(
        ["src/billing/a.py", "src/users/u.py"], [0, 1], edges=[{"source_cluster": 0, "target_cluster": 1, "count": 1}]
    )
    assert compute_intent_divergence(spec, partition).layer_violations == []


# IntentDivergence model


def test_total_violations_sum() -> None:
    div = IntentDivergence(
        misplaced_files=["a.py", "b.py"],
        unauthorized_cross_boundary=[{"from_module": "x", "to_module": "y", "count": 1}],
        layer_violations=[{"from_module": "y", "to_module": "z", "count": 2}],
    )
    assert div.total_violations == 4


def test_intent_divergence_to_dict() -> None:
    div = IntentDivergence(misplaced_files=["a.py"], unauthorized_cross_boundary=[], layer_violations=[])
    d = div.to_dict()
    assert d["total_violations"] == 1 and d["misplaced_files"] == ["a.py"]


def test_empty_partition_data_produces_no_violations() -> None:
    spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"])])
    assert compute_intent_divergence(spec, {}).total_violations == 0


# ruamel.yaml comment preservation


def test_ruamel_yaml_preserves_comments_on_round_trip(tmp_path: Path) -> None:
    """ruamel.yaml with typ='rt' preserves comments when loading and re-writing."""
    path = tmp_path / "boundaries.yaml"
    path.write_text(
        "# Architectural boundary rationale\n"
        "sdi_boundaries:\n"
        '  version: "0.1.0"  # spec schema version\n'
        "  modules: []\n",
        encoding="utf-8",
    )
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    with open(path, encoding="utf-8") as fh:
        data = yaml.load(fh)
    out_path = tmp_path / "out.yaml"
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh)
    result = out_path.read_text(encoding="utf-8")
    assert "Architectural boundary rationale" in result and "spec schema version" in result
