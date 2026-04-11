"""Java language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from Java source files.
Import paths are stored as dot-separated qualified names (e.g.
``java.util.List``). Wildcard imports end with ``.*`` (e.g. ``java.util.*``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tree_sitter_java as _tsja
from tree_sitter import Language, Node, Parser

from sdi.parsing._lang_common import _location, _structural_hash, _walk_nodes, count_loc
from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across calls in one process.
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    """Return the shared Java parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsja.language()))
    return _PARSER


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return node.text.decode("utf-8", errors="replace") if node.text else ""


def _extract_imports(root: Node) -> list[str]:
    """Walk the AST and collect all Java import declarations.

    For ``import java.util.List`` → ``"java.util.List"``.
    For ``import java.util.*`` → ``"java.util.*"``.

    Args:
        root: The program root AST node.

    Returns:
        Deduplicated list of qualified import path strings.
    """
    imports: list[str] = []
    for child in root.children:
        if child.type != "import_declaration":
            continue
        # The import text (minus 'import ' prefix and ';' suffix) is the path.
        # We reconstruct it from the node text directly.
        raw = _node_text(child)
        # Strip 'import ' prefix, optional 'static ' keyword, and trailing ';'
        raw = raw.removeprefix("import").strip()
        raw = raw.removeprefix("static").strip()
        raw = raw.rstrip(";").strip()
        if raw:
            imports.append(raw)

    seen: set[str] = set()
    result: list[str] = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            result.append(imp)
    return result


def _extract_symbols(root: Node) -> list[str]:
    """Extract top-level class and interface names from a Java file.

    Args:
        root: The program root AST node.

    Returns:
        List of class/interface name strings.
    """
    symbols: list[str] = []
    for node in root.children:
        if node.type in ("class_declaration", "interface_declaration",
                         "enum_declaration", "annotation_type_declaration"):
            for child in node.children:
                if child.type == "identifier":
                    symbols.append(_node_text(child))
                    break
    return symbols


def _extract_patterns(root: Node) -> list[dict[str, Any]]:
    """Extract structural pattern instances from a Java source file.

    Detects:
    - try/catch blocks (category: "error_handling")

    Args:
        root: The program root AST node.

    Returns:
        List of pattern instance dicts.
    """
    instances: list[dict[str, Any]] = []
    for node in _walk_nodes(root):
        if node.type == "try_statement":
            instances.append({
                "category": "error_handling",
                "ast_hash": _structural_hash(node),
                "location": _location(node),
            })
    return instances


class JavaAdapter(LanguageAdapter):
    """Tree-sitter based Java language adapter."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the adapter.

        Args:
            repo_root: Repository root directory.
        """
        self._repo_root = repo_root

    @property
    def language_name(self) -> str:
        """Return the canonical language name."""
        return "java"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".java"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a Java source file and extract a FeatureRecord.

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
