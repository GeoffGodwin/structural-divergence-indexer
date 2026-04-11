"""Tests for sdi.parsing.java — JavaAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing.java import JavaAdapter, count_loc
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> JavaAdapter:
    return JavaAdapter(repo_root)


def _parse(adapter: JavaAdapter, path: Path, source: str) -> FeatureRecord:
    """Write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# Import statements
# ---------------------------------------------------------------------------

class TestImportStatements:
    def test_simple_import(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "import java.util.List;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        assert "java.util.List" in record.imports

    def test_multiple_imports(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = (
            "import java.util.List;\n"
            "import java.util.Map;\n"
            "import com.example.Service;\n"
            "public class App {}\n"
        )
        record = _parse(adapter, path, source)
        assert "java.util.List" in record.imports
        assert "java.util.Map" in record.imports
        assert "com.example.Service" in record.imports

    def test_no_duplicate_imports(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = (
            "import java.util.List;\n"
            "import java.util.List;\n"
            "public class App {}\n"
        )
        record = _parse(adapter, path, source)
        assert record.imports.count("java.util.List") == 1


# ---------------------------------------------------------------------------
# Wildcard imports
# ---------------------------------------------------------------------------

class TestWildcardImports:
    def test_wildcard_import(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "import java.util.*;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        assert "java.util.*" in record.imports

    def test_specific_and_wildcard(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = (
            "import java.util.List;\n"
            "import java.io.*;\n"
            "public class App {}\n"
        )
        record = _parse(adapter, path, source)
        assert "java.util.List" in record.imports
        assert "java.io.*" in record.imports


# ---------------------------------------------------------------------------
# Package declarations
# ---------------------------------------------------------------------------

class TestPackageDeclarations:
    def test_package_not_in_imports(self, adapter: JavaAdapter, repo_root: Path) -> None:
        # Package declaration should NOT appear in imports
        path = repo_root / "App.java"
        source = "package com.example.app;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        assert "com.example.app" not in record.imports

    def test_package_with_imports(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = (
            "package com.example;\n"
            "import java.util.List;\n"
            "public class App {}\n"
        )
        record = _parse(adapter, path, source)
        assert "java.util.List" in record.imports
        assert "com.example" not in record.imports


# ---------------------------------------------------------------------------
# Class and interface definitions
# ---------------------------------------------------------------------------

class TestClassAndInterfaceDefinitions:
    def test_class_definition(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "public class MyService {}\n"
        record = _parse(adapter, path, source)
        assert "MyService" in record.symbols

    def test_interface_definition(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "public interface Runnable { void run(); }\n"
        record = _parse(adapter, path, source)
        assert "Runnable" in record.symbols

    def test_multiple_classes(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "public class Foo {}\nclass Bar {}\n"
        record = _parse(adapter, path, source)
        assert "Foo" in record.symbols
        assert "Bar" in record.symbols


# ---------------------------------------------------------------------------
# Pattern instances
# ---------------------------------------------------------------------------

class TestPatternInstances:
    def test_try_catch_detected(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = (
            "public class App {\n"
            "    void f() {\n"
            "        try { doThing(); } catch (Exception e) { }\n"
            "    }\n"
            "}\n"
        )
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_pattern_has_required_keys(
        self, adapter: JavaAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "App.java"
        source = (
            "public class App {\n"
            "    void f() { try { } catch (Exception e) { } }\n"
            "}\n"
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
    def test_language_is_java(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        record = _parse(adapter, path, "public class App {}\n")
        assert record.language == "java"

    def test_file_path_is_relative(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "pkg" / "App.java"
        record = _parse(adapter, path, "public class App {}\n")
        assert not Path(record.file_path).is_absolute()
        assert "pkg" in record.file_path

    def test_empty_file(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "Empty.java"
        record = _parse(adapter, path, "")
        assert record.imports == []
        assert record.symbols == []


# ---------------------------------------------------------------------------
# Static imports
# ---------------------------------------------------------------------------

class TestStaticImports:
    def test_static_import_simple(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "import static java.util.Collections.sort;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        assert "java.util.Collections.sort" in record.imports

    def test_static_import_wildcard(self, adapter: JavaAdapter, repo_root: Path) -> None:
        path = repo_root / "App.java"
        source = "import static java.lang.Math.*;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        assert "java.lang.Math.*" in record.imports

    def test_static_import_mixed_with_regular(
        self, adapter: JavaAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "App.java"
        source = (
            "import java.util.List;\n"
            "import static java.util.Collections.sort;\n"
            "public class App {}\n"
        )
        record = _parse(adapter, path, source)
        assert "java.util.List" in record.imports
        assert "java.util.Collections.sort" in record.imports

    def test_static_import_no_static_prefix_in_result(
        self, adapter: JavaAdapter, repo_root: Path
    ) -> None:
        # The word "static" must be stripped — it is not part of the path.
        path = repo_root / "App.java"
        source = "import static org.junit.Assert.assertEquals;\npublic class App {}\n"
        record = _parse(adapter, path, source)
        for imp in record.imports:
            assert not imp.startswith("static")


# ---------------------------------------------------------------------------
# count_loc — direct unit tests
# ---------------------------------------------------------------------------

class TestCountLoc:
    def test_empty_source_returns_zero(self) -> None:
        assert count_loc(b"") == 0

    def test_blank_lines_not_counted(self) -> None:
        assert count_loc(b"\n\n\n") == 0

    def test_line_comments_not_counted(self) -> None:
        source = b"// comment one\n// comment two\n"
        assert count_loc(source) == 0

    def test_code_lines_counted(self) -> None:
        source = b"public class App {}\n"
        assert count_loc(source) == 1

    def test_block_comment_single_line_not_counted(self) -> None:
        source = b"/* single line */\n"
        assert count_loc(source) == 0

    def test_javadoc_block_comment_not_counted(self) -> None:
        source = b"/**\n * Javadoc comment.\n */\n"
        assert count_loc(source) == 0

    def test_multiline_block_comment_not_counted(self) -> None:
        source = b"/*\n * line one\n * line two\n */\n"
        assert count_loc(source) == 0

    def test_code_after_block_comment_counted(self) -> None:
        source = b"/** doc */\npublic class App {}\n"
        # "/** doc */" starts with /* and contains */ on same line → skipped, not in block
        assert count_loc(source) == 1

    def test_mixed_code_comments_and_blanks(self) -> None:
        source = (
            b"// Header comment\n"        # line comment
            b"\n"                          # blank
            b"public class App {\n"       # code (+1)
            b"    /* note */\n"           # block comment (not at line start but stripped)
            b"    void run() {}\n"        # code (+1)
            b"}\n"                        # code (+1)
        )
        # "    /* note */" stripped → "/* note */", starts with /*
        assert count_loc(source) == 3

    def test_inline_comment_after_code_counts_line(self) -> None:
        source = b"int x = 1; // trailing comment\n"
        assert count_loc(source) == 1
