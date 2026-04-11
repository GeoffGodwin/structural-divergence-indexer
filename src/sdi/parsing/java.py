"""Java language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from Java source files.
Import paths are stored as dot-separated qualified names (e.g.
``java.util.List``). Wildcard imports end with ``.*`` (e.g. ``java.util.*``).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser
import tree_sitter_java as _tsja

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


def count_loc(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in Java source.

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
        if line.startswith("/*") or line.startswith("/**"):
            in_block_comment = True
            if "*/" in line[2:]:
                in_block_comment = False
            continue
        count += 1
    return count


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
