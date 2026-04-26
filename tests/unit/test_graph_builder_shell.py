"""Unit tests for shell import resolution in sdi.graph.builder."""

from __future__ import annotations

from sdi.config import SDIConfig
from sdi.graph.builder import _resolve_shell_import, build_dependency_graph
from sdi.parsing import FeatureRecord


def _make_config(weighted: bool = False) -> SDIConfig:
    cfg = SDIConfig()
    cfg.boundaries.weighted_edges = weighted
    return cfg


def _shell(path: str, imports: list[str]) -> FeatureRecord:
    return FeatureRecord(
        file_path=path,
        language="shell",
        imports=imports,
        symbols=[],
        pattern_instances=[],
        lines_of_code=10,
    )


def _py(path: str, imports: list[str]) -> FeatureRecord:
    return FeatureRecord(
        file_path=path,
        language="python",
        imports=imports,
        symbols=[],
        pattern_instances=[],
        lines_of_code=10,
    )


def _ts(path: str, imports: list[str]) -> FeatureRecord:
    return FeatureRecord(
        file_path=path,
        language="typescript",
        imports=imports,
        symbols=[],
        pattern_instances=[],
        lines_of_code=10,
    )


# ---------------------------------------------------------------------------
# _resolve_shell_import — unit tests
# ---------------------------------------------------------------------------


class TestResolveShellImport:
    def test_exact_match(self) -> None:
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("lib/util.sh", path_set) == "lib/util.sh"

    def test_missing_returns_none(self) -> None:
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("lib/missing.sh", path_set) is None

    def test_extensionless_resolves_to_sh(self) -> None:
        path_set = frozenset({"common.sh"})
        assert _resolve_shell_import("common", path_set) == "common.sh"

    def test_extensionless_prefers_sh_over_bash(self) -> None:
        path_set = frozenset({"common.sh", "common.bash"})
        # .sh is checked before .bash — must resolve to common.sh, not common.bash
        result = _resolve_shell_import("common", path_set)
        assert result == "common.sh"

    def test_explicit_sh_extension_no_fallback(self) -> None:
        path_set = frozenset({"common.sh"})
        assert _resolve_shell_import("common.sh", path_set) == "common.sh"

    def test_known_extension_skips_fallback(self) -> None:
        # "common.zsh" ends in a known shell ext → fallback to common.zsh.sh is skipped
        path_set = frozenset({"common.sh"})
        assert _resolve_shell_import("common.zsh", path_set) is None

    def test_bash_extension_skips_fallback(self) -> None:
        path_set = frozenset({"common.sh"})
        assert _resolve_shell_import("common.bash", path_set) is None

    def test_extensionless_bash_fallback(self) -> None:
        # Only common.bash in path_set → falls through .sh (not found), returns .bash
        path_set = frozenset({"common.bash"})
        assert _resolve_shell_import("common", path_set) == "common.bash"

    def test_cross_language_path_resolves(self) -> None:
        # Shell script sourcing a .py file that exists in the project
        path_set = frozenset({"scripts/env.py"})
        assert _resolve_shell_import("scripts/env.py", path_set) == "scripts/env.py"

    def test_empty_path_set(self) -> None:
        assert _resolve_shell_import("lib/util.sh", frozenset()) is None

    def test_subdir_extensionless(self) -> None:
        path_set = frozenset({"lib/util.sh", "lib/log.sh"})
        assert _resolve_shell_import("lib/util", path_set) == "lib/util.sh"


# ---------------------------------------------------------------------------
# build_dependency_graph — shell dispatch arm
# ---------------------------------------------------------------------------


class TestBuildDependencyGraphShell:
    def test_literal_match_produces_edge(self) -> None:
        records = [
            _shell("scripts/main.sh", ["lib/util.sh"]),
            _shell("lib/util.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0

    def test_missing_import_increments_unresolved(self) -> None:
        records = [
            _shell("scripts/main.sh", ["lib/missing.sh"]),
            _shell("lib/util.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 1

    def test_extensionless_resolves_to_sh(self) -> None:
        records = [
            _shell("scripts/main.sh", ["common"]),
            _shell("common.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0

    def test_extensionless_prefers_sh_over_bash(self) -> None:
        records = [
            _shell("scripts/main.sh", ["common"]),
            _shell("common.sh", []),
            _shell("common.bash", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        names = g.vs["name"]
        src_idx = names.index("scripts/main.sh")
        tgt_sh = names.index("common.sh")
        tgt_bash = names.index("common.bash")
        assert g.are_adjacent(src_idx, tgt_sh)
        assert not g.are_adjacent(src_idx, tgt_bash)

    def test_known_extension_no_fallback(self) -> None:
        # common.zsh is in imports but not in path_set; fallback must NOT
        # produce a spurious edge to common.sh
        records = [
            _shell("scripts/main.sh", ["common.zsh"]),
            _shell("common.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 1

    def test_self_import_increments_self_import_count(self) -> None:
        records = [_shell("scripts/main.sh", ["scripts/main.sh"])]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["self_import_count"] == 1

    def test_self_import_not_counted_as_unresolved(self) -> None:
        records = [_shell("scripts/main.sh", ["scripts/main.sh"])]
        _, meta = build_dependency_graph(records, _make_config())
        assert meta["unresolved_count"] == 0

    def test_empty_imports_no_edges(self) -> None:
        records = [_shell("lib/util.sh", [])]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 0
        assert meta["self_import_count"] == 0

    def test_cross_language_source(self) -> None:
        # Shell script sourcing a .py file that's in the project graph
        records = [
            _shell("scripts/setup.sh", ["scripts/env.py"]),
            _py("scripts/env.py", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0

    def test_mixed_language_three_edges(self) -> None:
        # One Python record, one shell record, one TS record — each produces one edge.
        # Verify the graph has exactly 3 edges with the correct (src, tgt) pairs.
        records = [
            _py("a.py", ["b"]),
            _py("b.py", []),
            _shell("run.sh", ["lib/helper.sh"]),
            _shell("lib/helper.sh", []),
            _ts("app.ts", ["./utils"]),
            _ts("utils.ts", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 3
        assert meta["unresolved_count"] == 0
        names = g.vs["name"]
        assert g.are_adjacent(names.index("a.py"), names.index("b.py"))
        assert g.are_adjacent(names.index("run.sh"), names.index("lib/helper.sh"))
        assert g.are_adjacent(names.index("app.ts"), names.index("utils.ts"))

    def test_weighted_shell_duplicate(self) -> None:
        # Two identical source literals in one file → weight == 2 with weighted=True
        records = [
            _shell("run.sh", ["lib/util.sh", "lib/util.sh"]),
            _shell("lib/util.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config(weighted=True))
        assert g.ecount() == 1
        assert g.es[0]["weight"] == 2

    def test_determinism(self) -> None:
        records = [
            _shell("entrypoint.sh", ["lib/a.sh", "lib/b.sh"]),
            _shell("lib/a.sh", ["lib/b.sh"]),
            _shell("lib/b.sh", []),
        ]
        g1, _ = build_dependency_graph(records, _make_config())
        g2, _ = build_dependency_graph(list(reversed(records)), _make_config())
        assert g1.vs["name"] == g2.vs["name"]
        assert g1.get_edgelist() == g2.get_edgelist()


# ---------------------------------------------------------------------------
# Gap 1: dot-command (.) form as source alias in _resolve_shell_import
# ---------------------------------------------------------------------------


class TestDotCommandForm:
    """Imports from the '.' (dot) directive are resolved identically to 'source'.

    _extract_imports in shell.py normalises both forms to the same repo-relative
    path string before building the FeatureRecord. These tests verify that
    _resolve_shell_import and build_dependency_graph handle those paths correctly —
    both with and without a file extension — covering the code path that processes
    '. ./lib/util' style directives.
    """

    def test_resolve_dot_command_extensionless(self) -> None:
        """'. ./lib/util' produces 'lib/util'; resolver finds 'lib/util.sh' via fallback."""
        path_set = frozenset({"lib/util.sh", "run.sh"})
        assert _resolve_shell_import("lib/util", path_set) == "lib/util.sh"

    def test_resolve_dot_command_with_sh_extension(self) -> None:
        """'. ./lib/util.sh' produces 'lib/util.sh'; resolver finds it via exact match."""
        path_set = frozenset({"lib/util.sh", "run.sh"})
        assert _resolve_shell_import("lib/util.sh", path_set) == "lib/util.sh"

    def test_resolve_dot_command_bare_filename_no_subdir(self) -> None:
        """'. common' from root-level script produces 'common'; fallback finds 'common.sh'."""
        path_set = frozenset({"common.sh"})
        assert _resolve_shell_import("common", path_set) == "common.sh"

    def test_build_graph_dot_command_extensionless_produces_edge(self) -> None:
        """build_dependency_graph resolves an extensionless import (from '. ./util') to an edge."""
        # '. ./util' from run.sh in repo root → shell adapter produces import "util"
        records = [
            _shell("run.sh", ["util"]),  # import from '. ./util'
            _shell("util.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0

    def test_build_graph_dot_command_with_extension_produces_edge(self) -> None:
        """build_dependency_graph resolves an import with .sh ext (from '. ./lib/util.sh') to an edge."""
        # '. ./lib/util.sh' from run.sh → shell adapter produces import "lib/util.sh"
        records = [
            _shell("run.sh", ["lib/util.sh"]),  # import from '. ./lib/util.sh'
            _shell("lib/util.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0

    def test_build_graph_dot_command_subdir_extensionless_produces_edge(self) -> None:
        """build_dependency_graph resolves '. ./lib/db' (subdir, no ext) to 'lib/db.sh'."""
        # '. ./lib/db' from entrypoint.sh → shell adapter produces "lib/db"
        records = [
            _shell("entrypoint.sh", ["lib/db"]),  # import from '. ./lib/db'
            _shell("lib/db.sh", []),
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 1
        assert meta["unresolved_count"] == 0
        names = g.vs["name"]
        assert g.are_adjacent(names.index("entrypoint.sh"), names.index("lib/db.sh"))

    def test_build_graph_dot_command_missing_returns_unresolved(self) -> None:
        """'. ./missing' with no match in project produces unresolved_count += 1, no edge."""
        records = [
            _shell("run.sh", ["missing"]),  # import from '. ./missing'; no match
        ]
        g, meta = build_dependency_graph(records, _make_config())
        assert g.ecount() == 0
        assert meta["unresolved_count"] == 1


# ---------------------------------------------------------------------------
# Gap 3: dynamic import strings ($VAR, backtick) → _resolve_shell_import None
# ---------------------------------------------------------------------------


class TestResolveShellImportDynamic:
    """_resolve_shell_import returns None for dynamic import strings without crashing.

    The shell adapter (_is_static_literal / _DYNAMIC_CHARS) filters out dynamic
    forms before building FeatureRecords, so these strings should never reach the
    resolver in normal operation. These tests verify the defensive behaviour:
    a malformed FeatureRecord with a dynamic import string must not produce a
    spurious edge and must not raise an exception.
    """

    def test_dollar_var_with_extension_returns_none(self) -> None:
        """'$LIB/util.sh' ends in .sh — exact match fails, fallback skipped, returns None."""
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("$LIB/util.sh", path_set) is None

    def test_dollar_brace_var_with_extension_returns_none(self) -> None:
        """'${LIB}/util.sh' ends in .sh — exact match fails, fallback skipped, returns None."""
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("${LIB}/util.sh", path_set) is None

    def test_dollar_var_extensionless_returns_none(self) -> None:
        """'$LIB/util' (no ext) — extension fallback tries '$LIB/util.sh', not in path_set."""
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("$LIB/util", path_set) is None

    def test_backtick_expression_returns_none(self) -> None:
        """Backtick command substitution form must return None without raising."""
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("`find . -name util`", path_set) is None

    def test_command_substitution_returns_none(self) -> None:
        """$(...) command substitution form must return None without raising."""
        path_set = frozenset({"lib/util.sh"})
        assert _resolve_shell_import("$(find . -name util)", path_set) is None

    def test_dynamic_string_against_empty_path_set_returns_none(self) -> None:
        """Dynamic string against empty path_set must return None, not raise."""
        assert _resolve_shell_import("$HOME/lib/util.sh", frozenset()) is None

    def test_dollar_star_glob_returns_none(self) -> None:
        """'lib/*.sh' (glob) must return None — exact match fails, glob is not a known ext."""
        path_set = frozenset({"lib/util.sh", "lib/log.sh"})
        assert _resolve_shell_import("lib/*.sh", path_set) is None
