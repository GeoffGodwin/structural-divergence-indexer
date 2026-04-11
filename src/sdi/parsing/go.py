"""Go language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from Go source files.
Import paths are stored as-is (slash-separated package paths, e.g.
``path/filepath`` or ``github.com/user/pkg``).
Only exported (capitalized) top-level identifiers are included in symbols.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from tree_sitter import Language, Node, Parser
import tree_sitter_go as _tsgo

from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across calls in one process.
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    """Return the shared Go parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsgo.language()))
    return _PARSER


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return node.text.decode("utf-8", errors="replace") if node.text else ""


def _extract_string_content(literal_node: Node) -> str | None:
    """Extract text from an interpreted_string_literal node.

    Args:
        literal_node: An ``interpreted_string_literal`` AST node.

    Returns:
        The unquoted string content, or None.
    """
    for child in literal_node.children:
        if child.type == "interpreted_string_literal_content":
            return _node_text(child)
    return None


def _extract_import_spec(spec_node: Node) -> str | None:
    """Extract the package path from a single import_spec node.

    Args:
        spec_node: An ``import_spec`` AST node.

    Returns:
        The package path string, or None.
    """
    for child in spec_node.children:
        if child.type == "interpreted_string_literal":
            return _extract_string_content(child)
    return None


def _extract_imports(root: Node) -> list[str]:
    """Walk the AST and collect all Go import package paths.

    Handles both single imports (``import "fmt"``) and grouped imports
    (``import ( "os"\n "path/filepath" )``).

    Args:
        root: The source_file root AST node.

    Returns:
        Deduplicated list of package path strings.
    """
    imports: list[str] = []
    for child in root.children:
        if child.type != "import_declaration":
            continue
        for sub in child.children:
            if sub.type == "import_spec":
                path = _extract_import_spec(sub)
                if path:
                    imports.append(path)
            elif sub.type == "import_spec_list":
                for spec in sub.children:
                    if spec.type == "import_spec":
                        path = _extract_import_spec(spec)
                        if path:
                            imports.append(path)

    seen: set[str] = set()
    result: list[str] = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            result.append(imp)
    return result


def _is_exported(name: str) -> bool:
    """Return True if the name starts with an uppercase letter (Go export rule)."""
    return bool(name) and name[0].isupper()


def _extract_symbols(root: Node) -> list[str]:
    """Extract top-level exported symbol names from a Go source file.

    Only includes exported (capitalized) functions, types, variables,
    and constants.

    Args:
        root: The source_file root AST node.

    Returns:
        List of exported symbol name strings.
    """
    symbols: list[str] = []
    for node in root.children:
        if node.type == "function_declaration":
            name = node.child_by_field_name("name")
            if name:
                text = _node_text(name)
                if _is_exported(text):
                    symbols.append(text)
        elif node.type in ("method_declaration",):
            name = node.child_by_field_name("name")
            if name:
                text = _node_text(name)
                if _is_exported(text):
                    symbols.append(text)
        elif node.type == "type_declaration":
            for sub in node.children:
                if sub.type == "type_spec":
                    name_node = sub.child_by_field_name("name")
                    if name_node:
                        text = _node_text(name_node)
                        if _is_exported(text):
                            symbols.append(text)
        elif node.type in ("var_declaration", "const_declaration"):
            for sub in node.children:
                if sub.type in ("var_spec", "const_spec"):
                    for name_node in sub.children:
                        if name_node.type == "identifier":
                            text = _node_text(name_node)
                            if _is_exported(text):
                                symbols.append(text)
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
    """Extract structural pattern instances from a Go source file.

    Detects:
    - if err != nil blocks (category: "error_handling")

    Args:
        root: The source_file root AST node.

    Returns:
        List of pattern instance dicts.
    """
    instances: list[dict[str, Any]] = []
    for node in _walk_nodes(root):
        # Go error handling: `if err != nil { ... }`
        # Acknowledged limitation: substring match on "err" will also trigger
        # on conditions like `if stderr != ""` or `if locker != nil`. This is
        # an accepted approximation consistent with SDI's measurement-not-
        # judgment principle — pattern counts are measurements, not verdicts.
        if node.type == "if_statement":
            cond = node.child_by_field_name("condition")
            if cond is not None and "err" in _node_text(cond):
                instances.append({
                    "category": "error_handling",
                    "ast_hash": _structural_hash(node),
                    "location": _location(node),
                })
    return instances


def count_loc(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in Go source.

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


class GoAdapter(LanguageAdapter):
    """Tree-sitter based Go language adapter."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the adapter.

        Args:
            repo_root: Repository root directory.
        """
        self._repo_root = repo_root

    @property
    def language_name(self) -> str:
        """Return the canonical language name."""
        return "go"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".go"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a Go source file and extract a FeatureRecord.

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
