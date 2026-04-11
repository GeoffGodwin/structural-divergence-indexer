"""Tests for sdi.parsing.python — PythonAdapter and helper functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing.python import (
    PythonAdapter,
    _extract_imports,
    _extract_symbols,
    _file_package,
    _resolve_relative_import,
)
from sdi.parsing._python_patterns import count_loc, extract_pattern_instances
from sdi.parsing import FeatureRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> PythonAdapter:
    return PythonAdapter(repo_root)


def _parse(adapter: PythonAdapter, path: Path, source: str) -> FeatureRecord:
    """Helper: write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# _file_package
# ---------------------------------------------------------------------------

class TestFilePackage:
    def test_src_layout_stripping(self, tmp_path: Path) -> None:
        path = tmp_path / "src" / "sdi" / "parsing" / "python.py"
        assert _file_package(path, tmp_path) == "sdi.parsing"

    def test_flat_layout(self, tmp_path: Path) -> None:
        path = tmp_path / "sdi" / "parsing" / "python.py"
        assert _file_package(path, tmp_path) == "sdi.parsing"

    def test_top_level_file(self, tmp_path: Path) -> None:
        path = tmp_path / "main.py"
        assert _file_package(path, tmp_path) == ""


# ---------------------------------------------------------------------------
# _resolve_relative_import
# ---------------------------------------------------------------------------

class TestResolveRelativeImport:
    def test_from_dot_import_foo(self) -> None:
        result = _resolve_relative_import(1, "foo", "sdi.parsing")
        assert result == "sdi.parsing.foo"

    def test_from_dotdot_import_bar(self) -> None:
        result = _resolve_relative_import(2, "bar", "sdi.parsing")
        assert result == "sdi.bar"

    def test_from_dot_no_module(self) -> None:
        # from . import foo → resolves to the current package
        result = _resolve_relative_import(1, None, "sdi.parsing")
        assert result == "sdi.parsing"

    def test_from_dotdot_utils_import_baz(self) -> None:
        result = _resolve_relative_import(2, "utils", "sdi.parsing")
        assert result == "sdi.utils"

    def test_top_level_package(self) -> None:
        result = _resolve_relative_import(1, "foo", "mypkg")
        assert result == "mypkg.foo"


# ---------------------------------------------------------------------------
# Import extraction tests (via parse_file)
# ---------------------------------------------------------------------------

class TestImportExtraction:
    def test_simple_import(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "import os\nimport sys\n")
        assert "os" in record.imports
        assert "sys" in record.imports

    def test_dotted_import(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "import os.path\n")
        assert "os.path" in record.imports

    def test_from_import(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "from pathlib import Path\n")
        assert "pathlib" in record.imports

    def test_relative_import_single_dot(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "pkg" / "sub" / "module.py"
        record = _parse(adapter, path, "from . import helper\n")
        assert "pkg.sub" in record.imports

    def test_relative_import_double_dot(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "pkg" / "sub" / "module.py"
        record = _parse(adapter, path, "from ..utils import bar\n")
        assert "pkg.utils" in record.imports

    def test_no_duplicate_imports(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "import os\nimport os\nfrom os import path\n"
        record = _parse(adapter, path, source)
        assert record.imports.count("os") == 1

    def test_empty_file(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "empty.py"
        record = _parse(adapter, path, "")
        assert record.imports == []
        assert record.symbols == []

    def test_aliased_import(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "import numpy as np\n")
        assert "numpy" in record.imports


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------

class TestSymbolExtraction:
    def test_function_definition(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "def my_func():\n    pass\n")
        assert "my_func" in record.symbols

    def test_class_definition(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "class MyClass:\n    pass\n")
        assert "MyClass" in record.symbols

    def test_top_level_constant(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "CONSTANT = 42\n")
        assert "CONSTANT" in record.symbols

    def test_decorated_function(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "@property\ndef my_prop(self):\n    pass\n"
        record = _parse(adapter, path, source)
        assert "my_prop" in record.symbols

    def test_multiple_symbols(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "class A:\n    pass\ndef b():\n    pass\nC = 1\n"
        record = _parse(adapter, path, source)
        assert "A" in record.symbols
        assert "b" in record.symbols
        assert "C" in record.symbols

    def test_nested_function_not_in_symbols(
        self, adapter: PythonAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.py"
        source = "def outer():\n    def inner():\n        pass\n"
        record = _parse(adapter, path, source)
        assert "outer" in record.symbols
        assert "inner" not in record.symbols


# ---------------------------------------------------------------------------
# Pattern instance tests
# ---------------------------------------------------------------------------

class TestPatternInstances:
    def test_try_except_detected(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "def f():\n    try:\n        pass\n    except ValueError:\n        pass\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_logging_call_detected(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "import logging\nlogger = logging.getLogger(__name__)\nlogger.info('hello')\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "logging" in categories

    def test_pattern_instance_has_required_keys(
        self, adapter: PythonAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.py"
        source = "def f():\n    try:\n        pass\n    except Exception:\n        pass\n"
        record = _parse(adapter, path, source)
        for pi in record.pattern_instances:
            assert "category" in pi
            assert "ast_hash" in pi
            assert "location" in pi
            assert "line" in pi["location"]

    def test_no_patterns_in_simple_file(
        self, adapter: PythonAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "main.py"
        source = "x = 1\ny = 2\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" not in categories

    def test_multiple_try_blocks(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = (
            "def f():\n"
            "    try:\n        pass\n    except ValueError:\n        pass\n"
            "def g():\n"
            "    try:\n        pass\n    except TypeError:\n        pass\n"
        )
        record = _parse(adapter, path, source)
        error_handling = [
            pi for pi in record.pattern_instances if pi["category"] == "error_handling"
        ]
        assert len(error_handling) == 2


# ---------------------------------------------------------------------------
# FeatureRecord metadata tests
# ---------------------------------------------------------------------------

class TestFeatureRecordMetadata:
    def test_file_path_is_relative(
        self, adapter: PythonAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "sub" / "mod.py"
        record = _parse(adapter, path, "x = 1\n")
        assert not Path(record.file_path).is_absolute()
        assert "sub" in record.file_path

    def test_language_is_python(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        record = _parse(adapter, path, "x = 1\n")
        assert record.language == "python"

    def test_loc_counts_code_lines(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "main.py"
        source = "# comment\n\nx = 1\ny = 2\n"
        record = _parse(adapter, path, source)
        assert record.lines_of_code == 2

    def test_syntax_error_raises(self, adapter: PythonAdapter, repo_root: Path) -> None:
        path = repo_root / "bad.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"def (broken syntax")
        # tree-sitter is error-tolerant; it won't raise on syntax errors.
        # The returned record should still be valid.
        record = adapter.parse_file(path, b"def (broken syntax")
        assert isinstance(record, FeatureRecord)


# ---------------------------------------------------------------------------
# LOC counter tests (unit)
# ---------------------------------------------------------------------------

class TestCountLoc:
    def test_empty(self) -> None:
        assert count_loc(b"") == 0

    def test_blank_lines_excluded(self) -> None:
        assert count_loc(b"\n\n\n") == 0

    def test_comment_lines_excluded(self) -> None:
        assert count_loc(b"# comment\n# another\n") == 0

    def test_code_lines_counted(self) -> None:
        assert count_loc(b"x = 1\ny = 2\n") == 2

    def test_mixed(self) -> None:
        src = b"# header\n\ndef foo():\n    pass\n"
        assert count_loc(src) == 2
