"""Tests for sdi.parsing.rust — RustAdapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdi.parsing.rust import RustAdapter, count_loc
from sdi.snapshot.model import FeatureRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def adapter(repo_root: Path) -> RustAdapter:
    return RustAdapter(repo_root)


def _parse(adapter: RustAdapter, path: Path, source: str) -> FeatureRecord:
    """Write source to path and parse it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return adapter.parse_file(path, source.encode("utf-8"))


# ---------------------------------------------------------------------------
# Use statements
# ---------------------------------------------------------------------------

class TestUseStatements:
    def test_stdlib_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use std::collections::HashMap;\n")
        assert "std::collections::HashMap" in record.imports

    def test_crate_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use crate::utils::foo;\n")
        assert "crate::utils::foo" in record.imports

    def test_super_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use super::module;\n")
        assert "super::module" in record.imports

    def test_grouped_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use crate::utils::{foo, bar};\n")
        # The base path should be recorded
        assert "crate::utils" in record.imports

    def test_no_duplicate_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        source = "use std::io;\nuse std::io;\n"
        record = _parse(adapter, path, source)
        assert record.imports.count("std::io") == 1

    def test_wildcard_use(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use std::io::*;\n")
        assert "std::io::*" in record.imports

    def test_wildcard_use_crate_path(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "use crate::prelude::*;\n")
        assert "crate::prelude::*" in record.imports


# ---------------------------------------------------------------------------
# Mod declarations
# ---------------------------------------------------------------------------

class TestModDeclarations:
    def test_external_mod_creates_import(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "mod submodule;\n")
        assert "./submodule" in record.imports

    def test_inline_mod_not_in_imports(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = "mod inline { pub fn inner() {} }\n"
        record = _parse(adapter, path, source)
        # Inline mods should NOT create file import entries
        assert "./inline" not in record.imports

    def test_multiple_external_mods(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = "mod models;\nmod handlers;\n"
        record = _parse(adapter, path, source)
        assert "./models" in record.imports
        assert "./handlers" in record.imports


# ---------------------------------------------------------------------------
# Pub items
# ---------------------------------------------------------------------------

class TestPubItems:
    def test_pub_function(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "pub fn greet() -> String { String::new() }\n")
        assert "greet" in record.symbols

    def test_private_function_excluded(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "fn private_fn() {}\n")
        assert "private_fn" not in record.symbols

    def test_pub_struct(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "pub struct MyStruct { pub x: i32 }\n")
        assert "MyStruct" in record.symbols

    def test_pub_enum(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "pub enum Status { Active, Inactive }\n")
        assert "Status" in record.symbols

    def test_pub_trait(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "pub trait Handler { fn handle(&self); }\n")
        assert "Handler" in record.symbols


# ---------------------------------------------------------------------------
# Trait and impl blocks
# ---------------------------------------------------------------------------

class TestTraitAndImplBlocks:
    def test_impl_block_records_type(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = "struct Foo; impl Foo { pub fn new() -> Self { Foo } }\n"
        record = _parse(adapter, path, source)
        assert "Foo" in record.symbols

    def test_trait_impl_records_self_type(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = (
            "pub trait MyTrait { fn do_it(&self); }\n"
            "struct Bar;\n"
            "impl MyTrait for Bar { fn do_it(&self) {} }\n"
        )
        record = _parse(adapter, path, source)
        assert "MyTrait" in record.symbols
        # Bar should appear from the impl
        assert "Bar" in record.symbols


# ---------------------------------------------------------------------------
# Pattern instances
# ---------------------------------------------------------------------------

class TestPatternInstances:
    def test_match_on_result_detected(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = (
            "fn f() {\n"
            "    match do_thing() {\n"
            "        Ok(v) => v,\n"
            "        Err(e) => panic!(\"{}\", e),\n"
            "    };\n"
            "}\n"
        )
        record = _parse(adapter, path, source)
        categories = [pi["category"] for pi in record.pattern_instances]
        assert "error_handling" in categories

    def test_pattern_has_required_keys(
        self, adapter: RustAdapter, repo_root: Path
    ) -> None:
        path = repo_root / "lib.rs"
        source = (
            "fn f() -> Result<(), ()> {\n"
            "    match Ok(()) { Ok(v) => Ok(v), Err(e) => Err(e) }\n"
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
    def test_language_is_rust(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "lib.rs"
        record = _parse(adapter, path, "fn main() {}\n")
        assert record.language == "rust"

    def test_file_path_is_relative(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "src" / "lib.rs"
        record = _parse(adapter, path, "fn main() {}\n")
        assert not Path(record.file_path).is_absolute()
        assert "src" in record.file_path

    def test_empty_file(self, adapter: RustAdapter, repo_root: Path) -> None:
        path = repo_root / "empty.rs"
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
        assert count_loc(b"\n\n\n") == 0

    def test_line_comments_not_counted(self) -> None:
        source = b"// single line comment\n// another comment\n"
        assert count_loc(source) == 0

    def test_doc_comments_not_counted(self) -> None:
        # Rust doc comments (/// and //!) are still line comments.
        source = b"/// Doc comment\n//! Module doc\n"
        assert count_loc(source) == 0

    def test_code_lines_counted(self) -> None:
        source = b"pub fn greet() {}\n"
        assert count_loc(source) == 1

    def test_block_comment_single_line_not_counted(self) -> None:
        source = b"/* block comment */\n"
        assert count_loc(source) == 0

    def test_multiline_block_comment_not_counted(self) -> None:
        source = b"/*\n * line one\n * line two\n */\n"
        assert count_loc(source) == 0

    def test_code_after_block_comment_counted(self) -> None:
        source = b"/* preamble */\npub fn main() {}\n"
        assert count_loc(source) == 1

    def test_mixed_code_comments_and_blanks(self) -> None:
        source = (
            b"// module header\n"         # line comment
            b"\n"                          # blank
            b"use std::io;\n"             # code (+1)
            b"/* config */\n"             # block comment
            b"pub fn run() {}\n"          # code (+1)
        )
        assert count_loc(source) == 2

    def test_inline_comment_after_code_counts_line(self) -> None:
        source = b"let x = 42; // the answer\n"
        assert count_loc(source) == 1
