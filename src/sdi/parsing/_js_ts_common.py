"""Shared utilities for TypeScript and JavaScript tree-sitter adapters.

Private module — used only by sdi.parsing.typescript and sdi.parsing.javascript.
"""

from __future__ import annotations

from typing import Any

from tree_sitter import Node

from sdi.parsing._lang_common import (  # noqa: F401 (count_loc re-exported to TS/JS adapters)
    _location,
    _structural_hash,
    _walk_nodes,
    count_loc,
)


def node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return node.text.decode("utf-8", errors="replace") if node.text else ""


def string_fragment(node: Node) -> str | None:
    """Extract the string content from a string literal node.

    Handles both single and double quoted strings by finding the
    string_fragment child node.

    Args:
        node: A ``string`` AST node.

    Returns:
        The unquoted string content, or None if not found.
    """
    for child in node.children:
        if child.type == "string_fragment":
            return node_text(child)
    return None


def _is_require_call(node: Node) -> str | None:
    """If node is a require('...') call, return the module path; else None."""
    if node.type != "call_expression":
        return None
    func = node.child_by_field_name("function")
    if func is None or node_text(func) != "require":
        return None
    args = node.child_by_field_name("arguments")
    if args is None:
        return None
    for child in args.children:
        if child.type == "string":
            return string_fragment(child)
    return None


def extract_require_imports(root: Node) -> list[str]:
    """Find all require('...') calls and return module paths.

    Args:
        root: Program root node.

    Returns:
        List of module path strings.
    """
    found: list[str] = []
    for node in _walk_nodes(root):
        path = _is_require_call(node)
        if path is not None:
            found.append(path)
    return found


def extract_es_imports(root: Node) -> list[str]:
    """Extract ES import statement module paths (non-type-only).

    For ``import { X } from './foo'`` → returns ``'./foo'``.
    Type-only imports are excluded here (handled by TypeScript adapter).

    Args:
        root: Program root node.

    Returns:
        List of module path strings.
    """
    found: list[str] = []
    for child in root.children:
        if child.type == "import_statement":
            # Skip type-only imports (TS: has a 'type' keyword child)
            has_type_keyword = any(c.type == "type" for c in child.children)
            if has_type_keyword:
                continue
            for c in child.children:
                if c.type == "string":
                    path = string_fragment(c)
                    if path is not None:
                        found.append(path)
    return found


def extract_reexport_imports(root: Node) -> list[str]:
    """Extract module paths from re-export statements.

    Covers ``export { X } from './foo'`` and ``export * from './foo'``.

    Args:
        root: Program root node.

    Returns:
        List of module path strings.
    """
    found: list[str] = []
    for child in root.children:
        if child.type == "export_statement":
            for c in child.children:
                if c.type == "string":
                    path = string_fragment(c)
                    if path is not None:
                        found.append(path)
    return found


def extract_symbols(root: Node) -> list[str]:
    """Extract top-level declared symbol names from a JS/TS program.

    Covers function declarations, class declarations, variable declarations,
    interface declarations, and type alias declarations.

    Args:
        root: Program root node.

    Returns:
        List of symbol name strings.
    """
    symbols: list[str] = []
    for node in root.children:
        kind = node.type
        if kind in ("function_declaration", "generator_function_declaration"):
            name = node.child_by_field_name("name")
            if name:
                symbols.append(node_text(name))
        elif kind == "class_declaration":
            name = node.child_by_field_name("name")
            if name:
                symbols.append(node_text(name))
        elif kind in ("interface_declaration", "type_alias_declaration"):
            # TypeScript-specific: interface Foo / type Foo = ...
            for c in node.children:
                if c.type == "type_identifier":
                    symbols.append(node_text(c))
                    break
        elif kind in ("lexical_declaration", "variable_declaration"):
            for c in node.children:
                if c.type == "variable_declarator":
                    name_node = c.child_by_field_name("name")
                    if name_node and name_node.type == "identifier":
                        symbols.append(node_text(name_node))
        elif kind == "export_statement":
            # export function ... / export class ... / export const ...
            for c in node.children:
                if c.type in ("function_declaration", "class_declaration"):
                    name = c.child_by_field_name("name")
                    if name:
                        symbols.append(node_text(name))
                    break
                elif c.type in (
                    "interface_declaration",
                    "type_alias_declaration",
                ):
                    for sub in c.children:
                        if sub.type == "type_identifier":
                            symbols.append(node_text(sub))
                            break
                    break
                elif c.type in ("lexical_declaration", "variable_declaration"):
                    for sub in c.children:
                        if sub.type == "variable_declarator":
                            name_node = sub.child_by_field_name("name")
                            if name_node and name_node.type == "identifier":
                                symbols.append(node_text(name_node))
                    break
    return symbols


def extract_pattern_instances(root: Node) -> list[dict[str, Any]]:
    """Extract structural pattern instances from a JS/TS program node.

    Detects:
    - try/catch blocks (category: "error_handling")
    - console.log / logger.* calls (category: "logging")

    Args:
        root: Program root node.

    Returns:
        List of pattern instance dicts with keys: category, ast_hash, location.
    """
    instances: list[dict[str, Any]] = []

    for node in _walk_nodes(root):
        if node.type == "try_statement":
            instances.append({
                "category": "error_handling",
                "ast_hash": _structural_hash(node),
                "location": _location(node),
            })
        elif node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func is not None:
                text = node_text(func).lower()
                if "." in text:
                    method = text.rsplit(".", 1)[-1]
                    logging_methods = {
                        "debug", "info", "warn", "warning", "error",
                        "critical", "exception", "log",
                    }
                    if method in logging_methods:
                        instances.append({
                            "category": "logging",
                            "ast_hash": _structural_hash(node),
                            "location": _location(node),
                        })

    return instances


