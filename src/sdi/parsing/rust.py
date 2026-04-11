"""Rust language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from Rust source files.

Import conventions in FeatureRecord.imports:
- ``use`` declarations: stored as ``::``-separated paths (e.g.
  ``std::collections::HashMap``, ``crate::utils``).
- External ``mod foo;`` declarations: stored as ``./foo`` (relative file path)
  since they create an implicit dependency on ``foo.rs`` or ``foo/mod.rs``.
  Inline ``mod foo { ... }`` blocks are NOT recorded (no file dependency).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser
import tree_sitter_rust as _tsr

from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across calls in one process.
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    """Return the shared Rust parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsr.language()))
    return _PARSER


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return node.text.decode("utf-8", errors="replace") if node.text else ""


def _extract_use_path(node: Node) -> list[str]:
    """Extract module paths from a use_declaration's path child.

    Handles:
    - ``scoped_identifier``: returns the full path as a single string.
    - ``scoped_use_list``: returns the base path (before ``{...}``).
    - ``identifier``: simple bare use (e.g., ``use foo``).

    Args:
        node: A use_declaration AST node.

    Returns:
        List of import path strings.
    """
    paths: list[str] = []
    for child in node.children:
        if child.type in ("scoped_identifier", "identifier"):
            text = _node_text(child).strip(";")
            if text:
                paths.append(text)
        elif child.type == "scoped_use_list":
            # Extract the base path before '::{'
            raw = _node_text(child)
            # e.g. "crate::utils::{foo, bar}" → "crate::utils"
            if "::{" in raw:
                base = raw[: raw.index("::{")]
                if base:
                    paths.append(base)
            else:
                # fallback: use whole text stripped of braces
                paths.append(raw)
        elif child.type == "use_wildcard":
            # use foo::*
            raw = _node_text(node).strip().rstrip(";").strip()
            if raw.startswith("use "):
                raw = raw[4:]
            paths.append(raw)
    return paths


def _extract_imports(root: Node) -> list[str]:
    """Walk the AST and collect all Rust import paths.

    Includes ``use`` declarations and external ``mod foo;`` declarations.

    Args:
        root: The source_file root AST node.

    Returns:
        Deduplicated list of import path strings.
    """
    imports: list[str] = []

    for child in root.children:
        if child.type == "use_declaration":
            imports.extend(_extract_use_path(child))
        elif child.type == "mod_item":
            # Only external mods (ending with ';') create file dependencies.
            has_body = any(c.type == "declaration_list" for c in child.children)
            if not has_body:
                name_node = child.child_by_field_name("name")
                if name_node:
                    imports.append(f"./{_node_text(name_node)}")

    seen: set[str] = set()
    result: list[str] = []
    for imp in imports:
        if imp and imp not in seen:
            seen.add(imp)
            result.append(imp)
    return result


def _is_pub(node: Node) -> bool:
    """Return True if the node has a ``pub`` visibility modifier."""
    for child in node.children:
        if child.type == "visibility_modifier":
            return True
    return False


def _extract_symbols(root: Node) -> list[str]:
    """Extract top-level public symbol names from a Rust source file.

    Includes pub functions, structs, enums, traits, type aliases,
    constants, and statics. impl blocks contribute the type name.

    Args:
        root: The source_file root AST node.

    Returns:
        List of symbol name strings.
    """
    symbols: list[str] = []
    for node in root.children:
        if node.type in (
            "function_item", "struct_item", "enum_item",
            "trait_item", "type_item", "const_item", "static_item",
        ):
            if _is_pub(node):
                name = node.child_by_field_name("name")
                if name:
                    symbols.append(_node_text(name))
        elif node.type == "impl_item":
            # impl Trait for Type or impl Type — record the self type
            type_nodes = [c for c in node.children if c.type == "type_identifier"]
            if type_nodes:
                # Last type_identifier is the self type (impl X / impl T for X)
                symbols.append(_node_text(type_nodes[-1]))
        elif node.type == "mod_item":
            name = node.child_by_field_name("name")
            if name and _is_pub(node):
                symbols.append(_node_text(name))
    return symbols


def _structural_hash(node: Node, max_depth: int = 6) -> str:
    """Hash the structural shape of an AST subtree."""
    def _serialize(n: Node, depth: int) -> str:
        if depth == 0:
            return n.type
        children = [_serialize(c, depth - 1) for c in n.children if not c.is_extra]
        return f"{n.type}({','.join(children)})"

    serialized = _serialize(node, max_depth)
    return hashlib.sha256(serialized.encode()).hexdigest()[:8]


def _location(node: Node) -> dict[str, int]:
    """Return the start line and column of a node (1-indexed line)."""
    return {"line": node.start_point[0] + 1, "col": node.start_point[1]}


def _walk_nodes(node: Node):
    """Yield all descendant nodes via depth-first traversal."""
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def _extract_patterns(root: Node) -> list[dict[str, Any]]:
    """Extract structural pattern instances from a Rust source file.

    Detects:
    - match expressions on Result/Option (category: "error_handling")

    Args:
        root: The source_file root AST node.

    Returns:
        List of pattern instance dicts.
    """
    instances: list[dict[str, Any]] = []
    for node in _walk_nodes(root):
        if node.type == "match_expression":
            # Heuristic: if any arm has Ok/Err/Some/None it's error handling.
            # Acknowledged approximation: "None" as a substring could match
            # enum variants like `NoneType` or string literals. Accepted per
            # SDI's measurement-not-judgment principle.
            text = _node_text(node)
            if any(kw in text for kw in ("Err", "Ok", "Some", "None")):
                instances.append({
                    "category": "error_handling",
                    "ast_hash": _structural_hash(node),
                    "location": _location(node),
                })
    return instances


def count_loc(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in Rust source.

    Args:
        source_bytes: Raw file bytes.

    Returns:
        Integer line count.
    """
    count = 0
    in_block_comment = False
    for raw_line in source_bytes.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if in_block_comment:
            if "*/" in line:
                in_block_comment = False
            continue
        if not line:
            continue
        if line.startswith("//"):
            continue
        if line.startswith("/*"):
            in_block_comment = True
            if "*/" in line[2:]:
                in_block_comment = False
            continue
        count += 1
    return count


class RustAdapter(LanguageAdapter):
    """Tree-sitter based Rust language adapter."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the adapter.

        Args:
            repo_root: Repository root directory.
        """
        self._repo_root = repo_root

    @property
    def language_name(self) -> str:
        """Return the canonical language name."""
        return "rust"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".rs"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a Rust source file and extract a FeatureRecord.

        The tree-sitter CST is discarded before this method returns.

        Args:
            path: Absolute path to the source file.
            source_bytes: Raw file contents.

        Returns:
            FeatureRecord with imports, symbols, pattern_instances, and loc.
        """
        parser = _get_parser()
        tree = parser.parse(source_bytes)
        root = tree.root_node

        imports = _extract_imports(root)
        symbols = _extract_symbols(root)
        pattern_instances = _extract_patterns(root)
        loc = count_loc(source_bytes)

        del tree, root

        rel_path = str(path.relative_to(self._repo_root))
        return FeatureRecord(
            file_path=rel_path,
            language=self.language_name,
            imports=imports,
            symbols=symbols,
            pattern_instances=pattern_instances,
            lines_of_code=loc,
        )
