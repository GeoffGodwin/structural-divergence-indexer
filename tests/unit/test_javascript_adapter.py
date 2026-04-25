"""Tests for sdi.parsing.javascript — JavaScriptAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing import FeatureRecord
from sdi.parsing.javascript import JavaScriptAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> JavaScriptAdapter:
    return JavaScriptAdapter(repo_root)


def _parse(adapter: JavaScriptAdapter, path: Path, source: str) -> FeatureRecord:
    """Write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# ES import extraction
# ---------------------------------------------------------------------------


class TestESImports:
    def test_named_import(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "import { foo } from './bar';\n")
        assert "./bar" in record.imports

    def test_default_import(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "import React from 'react';\n")
        assert "react" in record.imports

    def test_namespace_import(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "import * as _ from 'lodash';\n")
        assert "lodash" in record.imports

    def test_no_type_prefix_in_js(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        # JS does not support 'import type' — verify no type: prefix appears
        path = repo_root / "a.js"
        record = _parse(adapter, path, "import { foo } from './bar';\n")
        for imp in record.imports:
            assert not imp.startswith("type:")


# ---------------------------------------------------------------------------
# CommonJS require
# ---------------------------------------------------------------------------


class TestCommonJSRequire:
    def test_simple_require(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const x = require('./module');\n")
        assert "./module" in record.imports

    def test_destructured_require(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const { a, b } = require('./utils');\n")
        assert "./utils" in record.imports

    def test_require_deduplication(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        source = "const a = require('./mod');\nconst b = require('./mod');\n"
        record = _parse(adapter, path, source)
        assert record.imports.count("./mod") == 1


# ---------------------------------------------------------------------------
# Dynamic imports
# ---------------------------------------------------------------------------


class TestDynamicImports:
    def test_dynamic_import_expression(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const m = import('./dynamic');\n")
        assert "./dynamic" in record.imports

    def test_await_dynamic_import(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const m = await import('./lazy');\n")
        assert "./lazy" in record.imports


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------


class TestSymbolExtraction:
    def test_function_declaration(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "function greet() {}\n")
        assert "greet" in record.symbols

    def test_class_declaration(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "class MyClass {}\n")
        assert "MyClass" in record.symbols

    def test_const_declaration(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const CONST = 42;\n")
        assert "CONST" in record.symbols


# ---------------------------------------------------------------------------
# Pattern instances
# ---------------------------------------------------------------------------


class TestPatternInstances:
    def test_try_catch_detected(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        source = "try { doThing(); } catch (e) { console.error(e); }\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_logging_call_detected(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "console.log('hello');\n")
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "logging" in categories


# ---------------------------------------------------------------------------
# FeatureRecord metadata
# ---------------------------------------------------------------------------


class TestFeatureRecordMetadata:
    def test_language_is_javascript(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.js"
        record = _parse(adapter, path, "const x = 1;\n")
        assert record.language == "javascript"

    def test_empty_file(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "empty.js"
        record = _parse(adapter, path, "")
        assert record.imports == []
        assert record.symbols == []

    def test_file_path_relative(self, adapter: JavaScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "sub" / "mod.js"
        record = _parse(adapter, path, "const x = 1;\n")
        assert not Path(record.file_path).is_absolute()
