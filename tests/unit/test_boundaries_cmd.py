"""Unit tests for sdi.cli.boundaries_cmd — display helpers and sub-operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.cli.boundaries_cmd import (
    _do_export,
    _do_show,
    _spec_as_text,
)
from sdi.detection.boundaries import (
    AllowedCrossDomain,
    AspirationalSplit,
    BoundarySpec,
    LayersSpec,
    ModuleSpec,
    partition_to_proposed_yaml,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(
    *,
    version: str = "0.1.0",
    modules: list[ModuleSpec] | None = None,
    layers: LayersSpec | None = None,
    allowed: list[AllowedCrossDomain] | None = None,
    splits: list[AspirationalSplit] | None = None,
    last_ratified: str = "",
    ratified_by: str = "",
) -> BoundarySpec:
    return BoundarySpec(
        version=version,
        modules=modules or [],
        layers=layers,
        allowed_cross_domain=allowed or [],
        aspirational_splits=splits or [],
        last_ratified=last_ratified,
        ratified_by=ratified_by,
    )


def _pd(
    files: list[str],
    clusters: list[int],
) -> dict:
    return {
        "partition": clusters,
        "vertex_names": files,
        "inter_cluster_edges": [],
        "cluster_count": len(set(clusters)),
        "stability_score": 1.0,
    }


# ---------------------------------------------------------------------------
# _spec_as_text
# ---------------------------------------------------------------------------


class TestSpecAsText:
    """_spec_as_text() must format a BoundarySpec as readable text."""

    def test_includes_version(self) -> None:
        text = _spec_as_text(_spec(version="0.2.0"))
        assert "0.2.0" in text

    def test_includes_module_name(self) -> None:
        spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"])])
        text = _spec_as_text(spec)
        assert "billing" in text

    def test_includes_module_paths(self) -> None:
        spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/", "src/invoicing/"])])
        text = _spec_as_text(spec)
        assert "src/billing/" in text
        assert "src/invoicing/" in text

    def test_includes_layer_when_set(self) -> None:
        spec = _spec(modules=[ModuleSpec(name="web", paths=["src/web/"], layer="presentation")])
        text = _spec_as_text(spec)
        assert "presentation" in text

    def test_no_layer_line_when_not_set(self) -> None:
        spec = _spec(modules=[ModuleSpec(name="billing", paths=["src/billing/"])])
        text = _spec_as_text(spec)
        # Without a layer, layer= tag must not appear for that module
        assert "layer=None" not in text

    def test_includes_layers_ordering(self) -> None:
        layers = LayersSpec(ordering=["presentation", "domain", "infrastructure"], direction="downward")
        spec = _spec(layers=layers)
        text = _spec_as_text(spec)
        assert "presentation" in text
        assert "domain" in text
        assert "infrastructure" in text

    def test_includes_layers_direction(self) -> None:
        layers = LayersSpec(ordering=["presentation", "domain"], direction="downward")
        spec = _spec(layers=layers)
        text = _spec_as_text(spec)
        assert "downward" in text

    def test_includes_allowed_cross_domain(self) -> None:
        allowed = [AllowedCrossDomain(from_module="billing", to="users", reason="invoice needs user")]
        spec = _spec(
            modules=[
                ModuleSpec(name="billing", paths=["src/billing/"]),
                ModuleSpec(name="users", paths=["src/users/"]),
            ],
            allowed=allowed,
        )
        text = _spec_as_text(spec)
        assert "billing" in text
        assert "users" in text

    def test_includes_aspirational_splits(self) -> None:
        splits = [
            AspirationalSplit(
                current_module="billing",
                intended_boundary=["billing_core", "invoicing"],
                target_date="2026-Q3",
            )
        ]
        spec = _spec(splits=splits)
        text = _spec_as_text(spec)
        assert "billing_core" in text
        assert "invoicing" in text
        assert "2026-Q3" in text

    def test_includes_last_ratified_when_set(self) -> None:
        spec = _spec(last_ratified="2026-04-01T00:00:00Z", ratified_by="alice")
        text = _spec_as_text(spec)
        assert "2026-04-01T00:00:00Z" in text
        assert "alice" in text

    def test_no_last_ratified_line_when_empty(self) -> None:
        spec = _spec(last_ratified="", ratified_by="")
        text = _spec_as_text(spec)
        # Should not crash and should not include empty ratified line
        assert "Last ratified" not in text

    def test_returns_string(self) -> None:
        text = _spec_as_text(_spec())
        assert isinstance(text, str)

    def test_module_count_in_header(self) -> None:
        spec = _spec(
            modules=[
                ModuleSpec(name="a", paths=["src/a/"]),
                ModuleSpec(name="b", paths=["src/b/"]),
            ]
        )
        text = _spec_as_text(spec)
        assert "Modules (2)" in text


# ---------------------------------------------------------------------------
# partition_to_proposed_yaml
# ---------------------------------------------------------------------------


class TestPartitionToProposedYaml:
    """partition_to_proposed_yaml() generates a valid YAML skeleton."""

    def test_returns_string(self) -> None:
        result = partition_to_proposed_yaml(_pd([], []))
        assert isinstance(result, str)

    def test_contains_sdi_boundaries_key(self) -> None:
        result = partition_to_proposed_yaml(_pd([], []))
        assert "sdi_boundaries" in result

    def test_cluster_names_appear(self) -> None:
        pd = _pd(["src/a.py", "src/b.py"], [0, 1])
        result = partition_to_proposed_yaml(pd)
        assert "cluster_0" in result
        assert "cluster_1" in result

    def test_file_paths_appear_in_yaml(self) -> None:
        pd = _pd(["src/billing/a.py", "src/users/u.py"], [0, 1])
        result = partition_to_proposed_yaml(pd)
        assert "src/billing/a.py" in result
        assert "src/users/u.py" in result

    def test_limits_files_per_cluster_to_five(self) -> None:
        files = [f"src/a{i}.py" for i in range(10)]
        clusters = [0] * 10
        result = partition_to_proposed_yaml(_pd(files, clusters))
        # Only 5 files shown + a "and N more" comment
        assert "and 5 more" in result

    def test_no_limit_comment_when_five_or_fewer(self) -> None:
        files = [f"src/a{i}.py" for i in range(4)]
        clusters = [0] * 4
        result = partition_to_proposed_yaml(_pd(files, clusters))
        assert "more file" not in result

    def test_single_cluster_single_file(self) -> None:
        pd = _pd(["src/main.py"], [0])
        result = partition_to_proposed_yaml(pd)
        assert "cluster_0" in result
        assert "src/main.py" in result

    def test_contains_allowed_cross_domain_stub(self) -> None:
        result = partition_to_proposed_yaml(_pd(["src/a.py"], [0]))
        assert "allowed_cross_domain" in result

    def test_contains_version_field(self) -> None:
        result = partition_to_proposed_yaml(_pd(["src/a.py"], [0]))
        assert "0.1.0" in result


# ---------------------------------------------------------------------------
# _do_show
# ---------------------------------------------------------------------------


class TestDoShow:
    """_do_show() outputs the correct message based on spec presence."""

    def test_outputs_no_spec_message_when_spec_is_none(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        spec_path = tmp_path / "boundaries.yaml"
        _do_show(None, spec_path)
        out = capsys.readouterr().out
        assert "No boundary spec found" in out

    def test_no_spec_message_includes_spec_path(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        spec_path = tmp_path / "boundaries.yaml"
        _do_show(None, spec_path)
        out = capsys.readouterr().out
        assert str(spec_path) in out

    def test_outputs_spec_text_when_spec_present(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        spec = _spec(
            version="0.1.0",
            modules=[ModuleSpec(name="billing", paths=["src/billing/"])],
        )
        _do_show(spec, tmp_path / "boundaries.yaml")
        out = capsys.readouterr().out
        assert "billing" in out
        assert "0.1.0" in out

    def test_no_spec_message_suggests_propose_flag(self, capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
        _do_show(None, tmp_path / "boundaries.yaml")
        out = capsys.readouterr().out
        assert "--propose" in out


# ---------------------------------------------------------------------------
# _do_export
# ---------------------------------------------------------------------------


class TestDoExport:
    """_do_export() writes spec to file or exits 1 when no spec."""

    def test_exits_1_when_spec_is_none(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            _do_export(None, tmp_path / "out.txt")
        assert exc_info.value.code == 1

    def test_writes_file_when_spec_present(self, tmp_path: Path) -> None:
        spec = _spec(
            modules=[ModuleSpec(name="billing", paths=["src/billing/"])],
        )
        out_path = tmp_path / "exported.txt"
        _do_export(spec, out_path)
        assert out_path.exists()

    def test_written_file_contains_spec_content(self, tmp_path: Path) -> None:
        spec = _spec(
            modules=[ModuleSpec(name="billing", paths=["src/billing/"])],
        )
        out_path = tmp_path / "exported.txt"
        _do_export(spec, out_path)
        content = out_path.read_text(encoding="utf-8")
        assert "billing" in content

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        spec = _spec(modules=[ModuleSpec(name="a", paths=["src/a/"])])
        out_path = tmp_path / "nested" / "dir" / "spec.txt"
        _do_export(spec, out_path)
        assert out_path.exists()
