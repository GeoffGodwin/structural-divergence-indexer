"""Tests for sdi.parsing.typescript — TypeScriptAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing.typescript import TypeScriptAdapter, _build_imports, _extract_type_only_imports
from sdi.parsing._js_ts_common import extract_symbols, count_loc
from sdi.parsing import FeatureRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> TypeScriptAdapter:
    return TypeScriptAdapter(repo_root)


def _parse(adapter: TypeScriptAdapter, path: Path, source: str) -> FeatureRecord:
    """Write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# ES import extraction
# ---------------------------------------------------------------------------

class TestESImports:
    def test_named_import(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "import { foo } from './bar';\n")
        assert "./bar" in record.imports

    def test_default_import(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "import React from 'react';\n")
        assert "react" in record.imports

    def test_namespace_import(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "import * as _ from 'lodash';\n")
        assert "lodash" in record.imports

    def test_multiple_imports(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        source = "import { a } from './a';\nimport { b } from './b';\n"
        record = _parse(adapter, path, source)
        assert "./a" in record.imports
        assert "./b" in record.imports

    def test_no_duplicates(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        source = "import { a } from './mod';\nimport { b } from './mod';\n"
        record = _parse(adapter, path, source)
        assert record.imports.count("./mod") == 1


# ---------------------------------------------------------------------------
# Type-only imports
# ---------------------------------------------------------------------------

class TestTypeOnlyImports:
    def test_type_import_annotated(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "import type { Foo } from './types';\n")
        assert "type:./types" in record.imports

    def test_type_import_excluded_from_plain(
        self, adapter: TypeScriptAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "import type { Foo } from './types';\n")
        assert "./types" not in record.imports

    def test_mixed_type_and_value_imports(
        self, adapter: TypeScriptAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "a.ts"
        source = (
            "import { Foo } from './value';\n"
            "import type { Bar } from './types';\n"
        )
        record = _parse(adapter, path, source)
        assert "./value" in record.imports
        assert "type:./types" in record.imports
        assert "./types" not in record.imports


# ---------------------------------------------------------------------------
# CommonJS require
# ---------------------------------------------------------------------------

class TestCommonJSRequire:
    def test_require_statement(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "const x = require('./module');\n")
        assert "./module" in record.imports

    def test_destructured_require(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "const { a } = require('./utils');\n")
        assert "./utils" in record.imports


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------

class TestReExports:
    def test_named_reexport(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "export { foo } from './other';\n")
        assert "./other" in record.imports

    def test_star_reexport(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "export * from './reexport';\n")
        assert "./reexport" in record.imports


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

class TestSymbolExtraction:
    def test_function_declaration(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "function greet(name: string): void {}\n")
        assert "greet" in record.symbols

    def test_class_declaration(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "class MyClass {}\n")
        assert "MyClass" in record.symbols

    def test_interface_declaration(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "interface MyInterface { foo(): void; }\n")
        assert "MyInterface" in record.symbols

    def test_type_alias(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "type MyType = string | number;\n")
        assert "MyType" in record.symbols

    def test_exported_function(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "export function helper(): void {}\n")
        assert "helper" in record.symbols


# ---------------------------------------------------------------------------
# Pattern instances
# ---------------------------------------------------------------------------

class TestPatternInstances:
    def test_try_catch_detected(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        source = "try { doThing(); } catch (e) { console.error(e); }\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_logging_detected(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        source = "console.error('something went wrong');\n"
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "logging" in categories

    def test_pattern_has_required_keys(
        self, adapter: TypeScriptAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "a.ts"
        source = "try { x(); } catch (e) {}\n"
        record = _parse(adapter, path, source)
        for pi in record.pattern_instances:
            assert "category" in pi
            assert "ast_hash" in pi
            assert "location" in pi
            assert "line" in pi["location"]


# ---------------------------------------------------------------------------
# FeatureRecord metadata
# ---------------------------------------------------------------------------

class TestFeatureRecordMetadata:
    def test_language_is_typescript(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "a.ts"
        record = _parse(adapter, path, "const x = 1;\n")
        assert record.language == "typescript"

    def test_tsx_extension_supported(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "Component.tsx"
        record = _parse(adapter, path, "export function App() { return null; }\n")
        assert record.language == "typescript"

    def test_file_path_is_relative(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "sub" / "mod.ts"
        record = _parse(adapter, path, "const x = 1;\n")
        assert not Path(record.file_path).is_absolute()
        assert "sub" in record.file_path

    def test_empty_file(self, adapter: TypeScriptAdapter, repo_root: Path) -> None:
        path = repo_root / "empty.ts"
        record = _parse(adapter, path, "")
        assert record.imports == []
        assert record.symbols == []
