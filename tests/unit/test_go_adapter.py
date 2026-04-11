"""Tests for sdi.parsing.go — GoAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing.go import GoAdapter, count_loc
from sdi.parsing import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> GoAdapter:
    return GoAdapter(repo_root)


def _parse(adapter: GoAdapter, path: Path, source: str) -> FeatureRecord:
    """Write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# Import declarations
# ---------------------------------------------------------------------------

class TestImportDeclarations:
    def test_single_import(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        record = _parse(adapter, path, 'package main\nimport "fmt"\n')
        assert "fmt" in record.imports

    def test_grouped_imports(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = 'package main\nimport (\n    "os"\n    "path/filepath"\n)\n'
        record = _parse(adapter, path, source)
        assert "os" in record.imports
        assert "path/filepath" in record.imports

    def test_aliased_import(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = 'package main\nimport myfmt "fmt"\n'
        record = _parse(adapter, path, source)
        assert "fmt" in record.imports

    def test_blank_import(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = 'package main\nimport _ "unused/pkg"\n'
        record = _parse(adapter, path, source)
        assert "unused/pkg" in record.imports

    def test_third_party_import(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = 'package main\nimport "github.com/user/pkg"\n'
        record = _parse(adapter, path, source)
        assert "github.com/user/pkg" in record.imports

    def test_no_duplicate_imports(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = 'package main\nimport (\n    "fmt"\n    "fmt"\n)\n'
        record = _parse(adapter, path, source)
        assert record.imports.count("fmt") == 1


# ---------------------------------------------------------------------------
# Exported symbol detection
# ---------------------------------------------------------------------------

class TestExportedSymbols:
    def test_exported_function(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = "package main\nfunc Greet(name string) string { return name }\n"
        record = _parse(adapter, path, source)
        assert "Greet" in record.symbols

    def test_unexported_function_excluded(
        self, adapter: GoAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.go"
        source = "package main\nfunc helper() {}\n"
        record = _parse(adapter, path, source)
        assert "helper" not in record.symbols

    def test_exported_struct(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = "package main\ntype MyStruct struct { Name string }\n"
        record = _parse(adapter, path, source)
        assert "MyStruct" in record.symbols

    def test_unexported_struct_excluded(
        self, adapter: GoAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.go"
        source = "package main\ntype privateStruct struct { x int }\n"
        record = _parse(adapter, path, source)
        assert "privateStruct" not in record.symbols

    def test_exported_interface(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = "package main\ntype Handler interface { Handle() }\n"
        record = _parse(adapter, path, source)
        assert "Handler" in record.symbols


# ---------------------------------------------------------------------------
# Pattern instances
# ---------------------------------------------------------------------------

class TestPatternInstances:
    def test_error_check_detected(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        source = (
            "package main\n"
            "import \"errors\"\n"
            "func f() error {\n"
            "    err := errors.New(\"oops\")\n"
            "    if err != nil {\n"
            "        return err\n"
            "    }\n"
            "    return nil\n"
            "}\n"
        )
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_pattern_has_required_keys(
        self, adapter: GoAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.go"
        source = (
            "package main\n"
            "func f() { if err != nil { return } }\n"
        )
        record = _parse(adapter, path, source)
        for pi in record.pattern_instances:
            assert "category" in pi
            assert "ast_hash" in pi
            assert "location" in pi


# ---------------------------------------------------------------------------
# FeatureRecord metadata
# ---------------------------------------------------------------------------

class TestFeatureRecordMetadata:
    def test_language_is_go(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "main.go"
        record = _parse(adapter, path, "package main\n")
        assert record.language == "go"

    def test_file_path_is_relative(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "pkg" / "service.go"
        record = _parse(adapter, path, "package pkg\n")
        assert not Path(record.file_path).is_absolute()
        assert "pkg" in record.file_path

    def test_empty_file(self, adapter: GoAdapter, repo_root: Path) -> None:
        path = repo_root / "empty.go"
        record = _parse(adapter, path, "")
        assert record.imports == []
        assert record.symbols == []


# ---------------------------------------------------------------------------
# count_loc — direct unit tests
# ---------------------------------------------------------------------------

class TestCountLoc:
    def test_empty_source_returns_zero(self) -> None:
        assert count_loc(b"") == 0

    def test_blank_lines_not_counted(self) -> None:
        source = b"\n\n\n"
        assert count_loc(source) == 0

    def test_line_comments_not_counted(self) -> None:
        source = b"// this is a comment\n// another comment\n"
        assert count_loc(source) == 0

    def test_code_lines_counted(self) -> None:
        source = b"package main\nfunc main() {}\n"
        assert count_loc(source) == 2

    def test_single_line_block_comment_not_counted(self) -> None:
        source = b"/* single line block comment */\n"
        assert count_loc(source) == 0

    def test_multiline_block_comment_not_counted(self) -> None:
        source = b"/*\n * line one\n * line two\n */\n"
        assert count_loc(source) == 0

    def test_code_after_block_comment_counted(self) -> None:
        source = b"/*\n * doc\n */\npackage main\n"
        assert count_loc(source) == 1

    def test_mixed_code_and_comments(self) -> None:
        source = (
            b"package main\n"           # code  (+1)
            b"\n"                        # blank
            b"// imports\n"             # line comment
            b'import "fmt"\n'           # code  (+1)
            b"/* block */\n"            # block comment
            b"func main() {}\n"         # code  (+1)
        )
        assert count_loc(source) == 3

    def test_inline_comment_after_code_counts_line(self) -> None:
        # Lines that START with code but have a trailing comment are still code lines.
        source = b"x := 1 // assign\n"
        assert count_loc(source) == 1

    def test_block_comment_opening_and_close_on_same_line(self) -> None:
        # "/* ... */" on the same line should not enter block-comment mode
        source = b"/* a */ package main\n"
        # The line starts with /* and also contains */ so in_block_comment stays False.
        # Per the implementation, the line is skipped (starts with /*)
        # Verified: count_loc skips the whole line when it starts with /*
        assert count_loc(source) == 0
