"""Unit tests for sdi.graph._js_ts_resolver — JS/TS import resolution helpers.

Covers the four functions that have no existing tests in test_graph_builder.py:
_is_js_ts_file, _normalize_js_path, _build_js_path_set, _expand_alias_candidates.

Also includes a regression test for the M18 bug fix: _load_ts_path_aliases must
try plain json.loads before _strip_jsonc so that @/* path aliases are not
consumed as JSONC block comment starts when a "*/"-containing string appears
later in the same file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdi.graph._js_ts_resolver import (
    _build_js_path_set,
    _expand_alias_candidates,
    _is_js_ts_file,
    _load_ts_path_aliases,
    _normalize_js_path,
)

# ---------------------------------------------------------------------------
# _is_js_ts_file
# ---------------------------------------------------------------------------


class TestIsJsTsFile:
    @pytest.mark.parametrize(
        "path",
        [
            "foo.ts",
            "foo.tsx",
            "foo.js",
            "foo.jsx",
            "foo.mjs",
            "foo.cjs",
            "foo.d.ts",
            "src/components/Button.tsx",
            "lib/index.mjs",
        ],
    )
    def test_returns_true_for_js_ts_extensions(self, path: str) -> None:
        assert _is_js_ts_file(path) is True

    @pytest.mark.parametrize(
        "path",
        [
            "foo.py",
            "foo.go",
            "foo.rs",
            "foo.java",
            "foo.css",
            "foo.json",
            "foo.yaml",
            "foo.md",
            "Makefile",
            "foo",
            "foo.ts.backup",
        ],
    )
    def test_returns_false_for_non_js_ts_extensions(self, path: str) -> None:
        assert _is_js_ts_file(path) is False

    def test_case_sensitive_extension_check(self) -> None:
        # Extensions are case-sensitive; .TS is not recognised
        assert _is_js_ts_file("foo.TS") is False
        assert _is_js_ts_file("foo.JS") is False


# ---------------------------------------------------------------------------
# _normalize_js_path
# ---------------------------------------------------------------------------


class TestNormalizeJsPath:
    def test_strips_leading_dot_slash(self) -> None:
        assert _normalize_js_path("./foo.ts") == "foo.ts"

    def test_strips_nested_leading_dot_slash(self) -> None:
        assert _normalize_js_path("./foo/bar.ts") == "foo/bar.ts"

    def test_strips_multiple_leading_dot_slash(self) -> None:
        # While unusual, the while-loop must strip all chained "./" prefixes.
        assert _normalize_js_path("././foo.ts") == "foo.ts"

    def test_leaves_relative_parent_paths_alone(self) -> None:
        # "../foo" does not start with "./" so it is unchanged.
        assert _normalize_js_path("../foo.ts") == "../foo.ts"

    def test_replaces_backslash_with_forward_slash(self) -> None:
        assert _normalize_js_path("foo\\bar.ts") == "foo/bar.ts"

    def test_replaces_backslash_then_strips_dot_slash(self) -> None:
        # Backslash replacement happens before ./ stripping.
        assert _normalize_js_path(".\\foo.ts") == "foo.ts"

    def test_leaves_already_clean_path_unchanged(self) -> None:
        assert _normalize_js_path("src/index.ts") == "src/index.ts"

    def test_empty_string_unchanged(self) -> None:
        assert _normalize_js_path("") == ""


# ---------------------------------------------------------------------------
# _build_js_path_set
# ---------------------------------------------------------------------------


class TestBuildJsPathSet:
    def test_empty_input_returns_empty_set(self) -> None:
        assert _build_js_path_set(set()) == set()

    def test_filters_out_non_js_ts_files(self) -> None:
        paths = {"foo.py", "bar.go", "baz.ts"}
        result = _build_js_path_set(paths)
        assert result == {"baz.ts"}

    def test_normalizes_paths(self) -> None:
        paths = {"./src/index.ts"}
        result = _build_js_path_set(paths)
        assert "src/index.ts" in result
        assert "./src/index.ts" not in result

    def test_replaces_backslashes(self) -> None:
        paths = {"src\\components\\Button.tsx"}
        result = _build_js_path_set(paths)
        assert "src/components/Button.tsx" in result

    def test_all_js_ts_extensions_included(self) -> None:
        paths = {"a.ts", "b.tsx", "c.js", "d.jsx", "e.mjs", "f.cjs", "g.d.ts"}
        result = _build_js_path_set(paths)
        assert result == {"a.ts", "b.tsx", "c.js", "d.jsx", "e.mjs", "f.cjs", "g.d.ts"}

    def test_mixed_project_returns_only_js_ts(self) -> None:
        paths = {
            "src/index.ts",
            "src/style.css",
            "src/data.json",
            "src/utils.js",
            "README.md",
        }
        result = _build_js_path_set(paths)
        assert result == {"src/index.ts", "src/utils.js"}


# ---------------------------------------------------------------------------
# _expand_alias_candidates
# ---------------------------------------------------------------------------


class TestExpandAliasCandidates:
    def test_returns_none_when_no_aliases_match(self) -> None:
        aliases: list[tuple[str, list[str]]] = [("@/*", ["src/*"])]
        result = _expand_alias_candidates("react", aliases)
        assert result is None

    def test_returns_none_for_empty_alias_list(self) -> None:
        result = _expand_alias_candidates("@/lib/db", [])
        assert result is None

    def test_wildcard_alias_expands_captured_suffix(self) -> None:
        aliases = [("@/*", ["src/*"])]
        result = _expand_alias_candidates("@/lib/db", aliases)
        assert result == ["src/lib/db"]

    def test_exact_alias_match_returns_targets_unchanged(self) -> None:
        aliases = [("@app", ["src/app/index.ts"])]
        result = _expand_alias_candidates("@app", aliases)
        assert result == ["src/app/index.ts"]

    def test_multiple_targets_all_returned(self) -> None:
        aliases = [("@/*", ["src/*", "types/*"])]
        result = _expand_alias_candidates("@/models/user", aliases)
        assert result == ["src/models/user", "types/models/user"]

    def test_first_matching_alias_is_used(self) -> None:
        aliases = [
            ("@/*", ["first/*"]),
            ("@/*", ["second/*"]),
        ]
        result = _expand_alias_candidates("@/foo", aliases)
        assert result == ["first/foo"]

    def test_unmatched_prefix_skips_to_next_alias(self) -> None:
        aliases = [
            ("~/*", ["home/*"]),
            ("@/*", ["src/*"]),
        ]
        result = _expand_alias_candidates("@/bar", aliases)
        assert result == ["src/bar"]

    def test_returns_none_when_no_alias_prefix_matches(self) -> None:
        aliases = [("@/*", ["src/*"]), ("~/*", ["home/*"])]
        result = _expand_alias_candidates("./local", aliases)
        assert result is None


# ---------------------------------------------------------------------------
# _load_ts_path_aliases — M18 regression: @/* alias must not be corrupted
# ---------------------------------------------------------------------------


class TestLoadTsPathAliasesM18Regression:
    def test_at_wildcard_not_corrupted_when_later_string_contains_block_comment_end(self, tmp_path: Path) -> None:
        """Regression for M18 bug: plain-JSON tsconfig with @/* alias + a "*/"-containing
        string must parse correctly.

        Old code ran _strip_jsonc unconditionally. The block-comment regex would
        match from the `/*` inside "@/*" all the way to the first `*/` found in a
        later string value (e.g. an outDir value like "/* build */ dist"), eating the
        entire paths block and producing unparseable JSON.

        The M18 fix tries json.loads(text) first. Because the file is valid JSON,
        it succeeds without invoking _strip_jsonc.
        """
        tsconfig = {
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["./src/*"],
                },
                # This string value contains "*/" which would close a spurious
                # block comment opened by the `/*` in "@/*" under old code.
                "outDir": "/* build output */ dist",
            }
        }
        (tmp_path / "tsconfig.json").write_text(json.dumps(tsconfig))

        aliases = _load_ts_path_aliases(tmp_path)

        assert aliases == [("@/*", ["src/*"])], (
            "M18 regression: @/* path alias was corrupted. "
            "_load_ts_path_aliases must try plain json.loads before _strip_jsonc."
        )

    def test_multiple_at_style_aliases_all_loaded(self, tmp_path: Path) -> None:
        """All @/* alias entries must survive when the tsconfig has no JSONC comments."""
        tsconfig = {
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {
                    "@/*": ["./src/*"],
                    "@components/*": ["./src/components/*"],
                },
            }
        }
        (tmp_path / "tsconfig.json").write_text(json.dumps(tsconfig))

        aliases = _load_ts_path_aliases(tmp_path)

        # Both entries must be present (order depends on dict insertion order in Python 3.7+)
        alias_dict = dict(aliases)
        assert "@/*" in alias_dict
        assert "@components/*" in alias_dict
        assert alias_dict["@/*"] == ["src/*"]
        assert alias_dict["@components/*"] == ["src/components/*"]
