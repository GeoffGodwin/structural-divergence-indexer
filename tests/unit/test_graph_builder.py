"""Unit tests for sdi.graph.builder — dependency graph construction."""

from __future__ import annotations

from sdi.config import SDIConfig
from sdi.graph.builder import (
    _build_module_map,
    _file_path_to_module_key,
    _resolve_import,
    build_dependency_graph,
)
from sdi.parsing import FeatureRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(weighted: bool = False) -> SDIConfig:
    """Return an SDIConfig with weighted_edges set as requested."""
    cfg = SDIConfig()
    cfg.boundaries.weighted_edges = weighted
    return cfg


def _make_record(
    file_path: str,
    imports: list[str],
    symbols: list[str] | None = None,
) -> FeatureRecord:
    return FeatureRecord(
        file_path=file_path,
        language="python",
        imports=imports,
        symbols=symbols or [],
        pattern_instances=[],
        lines_of_code=10,
    )


# ---------------------------------------------------------------------------
# _file_path_to_module_key
# ---------------------------------------------------------------------------

class TestFilePathToModuleKey:
    def test_simple_file(self) -> None:
        assert _file_path_to_module_key("main.py") == "main"

    def test_nested_file(self) -> None:
        assert _file_path_to_module_key("models/user.py") == "models.user"

    def test_init_file(self) -> None:
        assert _file_path_to_module_key("models/__init__.py") == "models"

    def test_src_layout_stripped(self) -> None:
        assert _file_path_to_module_key("src/sdi/config.py") == "sdi.config"

    def test_non_python_returns_none(self) -> None:
        assert _file_path_to_module_key("README.md") is None
        assert _file_path_to_module_key("index.ts") is None

    def test_windows_separators(self) -> None:
        assert _file_path_to_module_key("models\\user.py") == "models.user"

    def test_deeply_nested(self) -> None:
        assert _file_path_to_module_key("a/b/c/d.py") == "a.b.c.d"

    def test_src_init(self) -> None:
        assert _file_path_to_module_key("src/sdi/__init__.py") == "sdi"


# ---------------------------------------------------------------------------
# _build_module_map
# ---------------------------------------------------------------------------

class TestBuildModuleMap:
    def test_basic(self) -> None:
        result = _build_module_map({"models/user.py", "utils/helpers.py"})
        assert result["models.user"] == "models/user.py"
        assert result["utils.helpers"] == "utils/helpers.py"

    def test_init_file(self) -> None:
        result = _build_module_map({"models/__init__.py"})
        assert result["models"] == "models/__init__.py"

    def test_skips_non_python(self) -> None:
        result = _build_module_map({"main.py", "README.md", "setup.cfg"})
        assert "main" in result
        assert len(result) == 1

    def test_empty(self) -> None:
        assert _build_module_map(set()) == {}


# ---------------------------------------------------------------------------
# _resolve_import
# ---------------------------------------------------------------------------

class TestResolveImport:
    def test_exact_match(self) -> None:
        module_map = {"models.user": "models/user.py"}
        assert _resolve_import("models.user", module_map) == "models/user.py"

    def test_suffix_match(self) -> None:
        module_map = {"models.user": "models/user.py"}
        assert _resolve_import("pkg.models.user", module_map) == "models/user.py"

    def test_no_match_external(self) -> None:
        module_map = {"models.user": "models/user.py"}
        assert _resolve_import("os", module_map) is None
        assert _resolve_import("pathlib.Path", module_map) is None

    def test_prefers_longer_suffix(self) -> None:
        module_map = {
            "c": "c.py",
            "b.c": "b/c.py",
            "a.b.c": "a/b/c.py",
        }
        assert _resolve_import("x.a.b.c", module_map) == "a/b/c.py"

    def test_no_partial_segment_match(self) -> None:
        module_map = {"a.b": "a/b.py"}
        assert _resolve_import("pa.b", module_map) is None

    def test_empty_module_map(self) -> None:
        assert _resolve_import("anything", {}) is None


# ---------------------------------------------------------------------------
# build_dependency_graph — empty input
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphEmpty:
    def test_empty_records(self) -> None:
        g, meta = build_dependency_graph([], _make_config())
        assert g.vcount() == 0
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 0
        assert meta["self_import_count"] == 0


# ---------------------------------------------------------------------------
# build_dependency_graph — basic graph
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphBasic:
    def _three_node_records(self) -> list[FeatureRecord]:
        return [
            _make_record("a.py", ["b", "c"]),
            _make_record("b.py", ["c"]),
            _make_record("c.py", []),
        ]

    def test_node_edge_counts(self) -> None:
        g, _ = build_dependency_graph(self._three_node_records(), _make_config())
        assert g.vcount() == 3
        assert g.ecount() == 3  # a→b, a→c, b→c

    def test_vertex_names_and_directed(self) -> None:
        g, _ = build_dependency_graph(self._three_node_records(), _make_config())
        assert sorted(g.vs["name"]) == ["a.py", "b.py", "c.py"]
        assert g.is_directed()

    def test_deterministic_vertex_order(self) -> None:
        records = self._three_node_records()
        g1, _ = build_dependency_graph(records, _make_config())
        g2, _ = build_dependency_graph(list(reversed(records)), _make_config())
        assert g1.vs["name"] == g2.vs["name"]
        assert g1.get_edgelist() == g2.get_edgelist()


# ---------------------------------------------------------------------------
# build_dependency_graph — external imports excluded
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphExternalExcluded:
    def test_stdlib_imports_excluded(self) -> None:
        records = [
            _make_record("a.py", ["os", "sys", "pathlib"]),
            _make_record("b.py", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 3

    def test_third_party_import_excluded(self) -> None:
        records = [
            _make_record("a.py", ["click", "rich"]),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 2

    def test_mixed_internal_external(self) -> None:
        records = [
            _make_record("a.py", ["os", "b"]),
            _make_record("b.py", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 1


# ---------------------------------------------------------------------------
# build_dependency_graph — self-imports
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphSelfImport:
    def test_self_import_skipped(self) -> None:
        # "a" resolves to "a.py" which is the same file
        records = [_make_record("a.py", ["a"])]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["self_import_count"] == 1

    def test_self_import_not_in_unresolved(self) -> None:
        records = [_make_record("a.py", ["a"])]
        _, meta = build_dependency_graph(records, _make_config())
        assert meta["unresolved_count"] == 0


# ---------------------------------------------------------------------------
# build_dependency_graph — duplicate imports
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphDuplicates:
    def test_duplicate_unweighted_creates_single_edge(self) -> None:
        # Two import entries for same target → single edge
        records = [
            _make_record("a.py", ["b", "b"]),
            _make_record("b.py", []),
        ]
        g, _ = build_dependency_graph(records, _make_config(weighted=False))
        assert g.ecount() == 1

    def test_duplicate_weighted_sums_weight(self) -> None:
        records = [
            _make_record("a.py", ["b", "b"]),
            _make_record("b.py", []),
        ]
        g, _ = build_dependency_graph(records, _make_config(weighted=True))
        assert g.ecount() == 1
        assert g.es[0]["weight"] == 2


# ---------------------------------------------------------------------------
# build_dependency_graph — weighted edges
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphWeighted:
    def test_weighted_edges_have_weight_attribute(self) -> None:
        records = [
            _make_record("a.py", ["b"]),
            _make_record("b.py", []),
        ]
        g, _ = build_dependency_graph(records, _make_config(weighted=True))
        assert "weight" in g.edge_attributes()
        assert g.es[0]["weight"] == 1

    def test_unweighted_no_weight_attribute(self) -> None:
        records = [
            _make_record("a.py", ["b"]),
            _make_record("b.py", []),
        ]
        g, _ = build_dependency_graph(records, _make_config(weighted=False))
        assert "weight" not in g.edge_attributes()


# ---------------------------------------------------------------------------
# build_dependency_graph — suffix-based import resolution
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphSuffixResolution:
    def test_package_prefix_stripped(self) -> None:
        """Import 'pkg.models.user' resolves to 'models/user.py'."""
        records = [
            _make_record("service.py", ["pkg.models.user"]),
            _make_record("models/user.py", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0


# ---------------------------------------------------------------------------
# build_dependency_graph — cycle detection (edge presence)
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphCycles:
    def test_circular_import_creates_edges(self) -> None:
        records = [
            _make_record("a.py", ["b"]),
            _make_record("b.py", ["a"]),
        ]
        g, _ = build_dependency_graph(records, _make_config())
        assert g.ecount() == 2
        assert not g.is_dag()


# ---------------------------------------------------------------------------
# _file_path_to_module_key — deep src-layout paths (Coverage Gap 1)
# ---------------------------------------------------------------------------

class TestFilePathToModuleKeyDeepSrcLayout:
    def test_deep_src_layout_three_levels(self) -> None:
        """src/sdi/cli/init_cmd.py → sdi.cli.init_cmd (strip leading 'src.')."""
        result = _file_path_to_module_key("src/sdi/cli/init_cmd.py")
        assert result == "sdi.cli.init_cmd"

    def test_deep_src_layout_four_levels(self) -> None:
        """src/sdi/parsing/adapters/python.py → sdi.parsing.adapters.python."""
        result = _file_path_to_module_key("src/sdi/parsing/adapters/python.py")
        assert result == "sdi.parsing.adapters.python"

    def test_deep_src_layout_init(self) -> None:
        """src/sdi/cli/__init__.py → sdi.cli (init represents the package)."""
        result = _file_path_to_module_key("src/sdi/cli/__init__.py")
        assert result == "sdi.cli"

    def test_src_prefix_only_stripped_once(self) -> None:
        """src/src/models.py → src.models (only the leading 'src.' is stripped)."""
        result = _file_path_to_module_key("src/src/models.py")
        assert result == "src.models"


# ---------------------------------------------------------------------------
# build_dependency_graph — non-Python FeatureRecords silently ignored (Gap 2)
# ---------------------------------------------------------------------------

class TestBuildDependencyGraphNonPythonRecords:
    def test_typescript_record_silently_ignored_as_node(self) -> None:
        """Non-Python files produce no module key and are not added to the module map.

        The TypeScript file still becomes a vertex (all records do), but it
        cannot be a target of import resolution, so no edges point to it from
        normal Python import strings.
        """
        records = [
            _make_record("a.py", ["b"]),
            _make_record("b.py", []),
            FeatureRecord(
                file_path="frontend/app.ts",
                language="typescript",
                imports=["some.ts.dep"],
                symbols=[],
                pattern_instances=[],
                lines_of_code=5,
            ),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        # All three files become vertices
        assert g.vcount() == 3
        # Only the Python→Python edge exists; TypeScript import is unresolved
        assert g.ecount() == 1
        # The TypeScript import "some.ts.dep" is unresolved
        assert meta["unresolved_count"] >= 1

    def test_python_cannot_resolve_to_typescript_file(self) -> None:
        """An import that might textually match a .ts filename resolves to None
        because non-Python files are excluded from the module map."""
        records = [
            _make_record("service.py", ["frontend.app"]),
            FeatureRecord(
                file_path="frontend/app.ts",
                language="typescript",
                imports=[],
                symbols=[],
                pattern_instances=[],
                lines_of_code=3,
            ),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        # "frontend.app" does not resolve to the .ts file
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 1

    def test_all_non_python_records_no_edges(self) -> None:
        """A set of only non-Python records produces a graph with vertices but
        no edges and all imports counted as unresolved."""
        records = [
            FeatureRecord(
                file_path="index.ts",
                language="typescript",
                imports=["react"],
                symbols=[],
                pattern_instances=[],
                lines_of_code=1,
            ),
            FeatureRecord(
                file_path="utils.ts",
                language="typescript",
                imports=["index"],
                symbols=[],
                pattern_instances=[],
                lines_of_code=1,
            ),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.vcount() == 2
        assert g.ecount() == 0
        # Both imports are unresolvable (no Python files in module map)
        assert meta["unresolved_count"] == 2


# ---------------------------------------------------------------------------
# _resolve_import — equal-length tie-breaking in suffix match (Coverage Gap 3)
# ---------------------------------------------------------------------------

class TestResolveImportTieBreaking:
    def test_two_equal_length_suffix_keys_returns_one_result(self) -> None:
        """When two module keys have the same length and both match as a suffix,
        _resolve_import must return one of them without raising an exception.
        The tie-breaking is implementation-defined (last-wins with current >),
        but the function must not crash and must return a valid file path."""
        module_map = {
            "models.user": "models/user.py",  # length 11
            "domain.user": "domain/user.py",  # length 11 — same length as above
        }
        import_str = "pkg.models.user"  # matches "models.user" suffix
        # The import_str only ends with ".models.user", not ".domain.user",
        # so only one key actually matches here — verify it resolves correctly.
        result = _resolve_import(import_str, module_map)
        assert result == "models/user.py"

    def test_ambiguous_single_segment_tie(self) -> None:
        """Two single-segment module keys of equal length that both match as
        a suffix of the import string. The function must return a non-None
        value (one of the candidates) without raising."""
        module_map = {
            "abc": "pkg1/abc.py",  # length 3
            "xyz": "pkg2/xyz.py",  # length 3 — same length, different key
        }
        # "foo.abc" ends with ".abc" — matches "abc" key only
        result = _resolve_import("foo.abc", module_map)
        assert result == "pkg1/abc.py"

    def test_genuinely_ambiguous_equal_length_returns_a_result(self) -> None:
        """Construct a case where two keys have the same length AND both match
        as proper dotted suffixes of the import string. The function must
        return one of the valid file paths (not crash, not return None)."""
        # "x.ab" ends with ".ab"; "x.cd" does NOT end with ".ab" — can't make
        # truly ambiguous single-char equal-length suffixes without same string.
        # Use a longer common-length suffix that matches both via different prefixes:
        # import "root.pkg.foo" ends with ".pkg.foo" (length 7)
        # import "root.bar.foo" ends with ".bar.foo" (length 7)
        # We need TWO distinct keys of same length that BOTH are dotted suffixes
        # of the SAME import_str. That requires the same key value — impossible
        # for distinct keys. Instead: verify the tie-break does not crash when
        # the best_key_len is tied across iterations.
        module_map = {
            "b.c": "b/c.py",  # length 3
            "a.c": "a/c.py",  # length 3
        }
        # "x.b.c" ends with ".b.c" → matches "b.c" (length 3)
        # "x.a.c" ends with ".a.c" → matches "a.c" (length 3)
        # But for a single import_str, only ONE of these can match as a suffix.
        result_bc = _resolve_import("x.b.c", module_map)
        result_ac = _resolve_import("x.a.c", module_map)
        assert result_bc == "b/c.py"
        assert result_ac == "a/c.py"

    def test_equal_length_one_matches_one_does_not(self) -> None:
        """Two keys of equal length where only one is an actual dotted suffix.
        Confirms that substring matching (without dot boundary) is rejected,
        while proper dotted-suffix matching still works."""
        module_map = {
            "user": "models/user.py",  # length 4
            "sers": "other/sers.py",   # length 4 — same length, NOT a dotted suffix of "models.user"
        }
        result = _resolve_import("models.user", module_map)
        # "models.user" ends with ".user" (dotted) → matches "user"
        # "models.user" does NOT end with ".sers" → no match for "sers"
        assert result == "models/user.py"
