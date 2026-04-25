"""Python language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from Python source files.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_python as _tsp
from tree_sitter import Language, Node, Parser

from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across all calls in one process.
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    """Return the shared Python parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsp.language()))
    return _PARSER


# ---------------------------------------------------------------------------
# Import extraction
# ---------------------------------------------------------------------------


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return node.text.decode("utf-8", errors="replace") if node.text else ""


def _extract_dotted_name(node: Node) -> str:
    """Extract a dotted name (e.g. 'pathlib.Path') from a dotted_name node."""
    return _node_text(node).strip()


def _resolve_relative_import(
    dots: int,
    module: str | None,
    file_package: str,
) -> str:
    """Resolve a relative import to an absolute module path.

    Args:
        dots: Number of leading dots (1 = current package, 2 = parent, ...).
        module: Module name after the dots, or None for bare ``from . import``.
        file_package: Dotted package path of the importing file
            (e.g. "sdi.parsing" for ``src/sdi/parsing/python.py``).

    Returns:
        Absolute dotted module path string.
    """
    parts = file_package.split(".") if file_package else []
    # Remove (dots - 1) trailing components to get the anchor package
    anchor_parts = parts[: max(0, len(parts) - (dots - 1))]
    if module:
        return ".".join(anchor_parts + [module]) if anchor_parts else module
    return ".".join(anchor_parts) if anchor_parts else ""


def _file_package(path: Path, repo_root: Path) -> str:
    """Infer the Python package path for a file.

    Strips common source roots (``src/``) and converts path separators to dots.

    Args:
        path: Absolute path to the Python file.
        repo_root: Repository root directory.

    Returns:
        Dotted package string, e.g. "sdi.parsing" for src/sdi/parsing/foo.py.
    """
    rel = path.relative_to(repo_root)
    parts = list(rel.parts)
    # Strip leading 'src' directory if present (src layout)
    if parts and parts[0] == "src":
        parts = parts[1:]
    # Drop the filename itself to get the package
    package_parts = parts[:-1]
    return ".".join(package_parts)


def _extract_imports(root: Node, file_pkg: str) -> list[str]:
    """Walk the AST and collect all import targets as absolute module paths.

    Args:
        root: The module-level AST node.
        file_pkg: The file's package path (for relative import resolution).

    Returns:
        Deduplicated list of absolute module path strings.
    """
    imports: list[str] = []

    for node in root.children:
        if node.type == "import_statement":
            # import os  /  import os.path  /  import a, b
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(_extract_dotted_name(child))
                elif child.type == "aliased_import":
                    # import os as operating_system
                    for subchild in child.children:
                        if subchild.type == "dotted_name":
                            imports.append(_extract_dotted_name(subchild))
                            break

        elif node.type == "import_from_statement":
            imports.extend(_extract_from_import(node, file_pkg))

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for imp in imports:
        if imp and imp not in seen:
            seen.add(imp)
            result.append(imp)
    return result


def _extract_from_import(node: Node, file_pkg: str) -> list[str]:
    """Extract imports from a single import_from_statement node.

    For ``from X import Y``, X is the module (what we track).
    Imported names (Y) are ignored — only the source module matters.
    """
    imports: list[str] = []
    module_name: str | None = None
    dots = 0
    is_relative = False
    saw_import_keyword = False

    for child in node.children:
        if child.type == "relative_import":
            is_relative = True
            for subchild in child.children:
                if subchild.type == "import_prefix":
                    dots = len(_node_text(subchild))
                elif subchild.type == "dotted_name":
                    module_name = _extract_dotted_name(subchild)
        elif child.type == "import":
            # Everything after 'import' keyword is the imported symbol list
            saw_import_keyword = True
        elif child.type == "dotted_name" and not is_relative and not saw_import_keyword:
            # First dotted_name before 'import' keyword is the source module
            module_name = _extract_dotted_name(child)

    if is_relative:
        resolved = _resolve_relative_import(dots, module_name, file_pkg)
        if resolved:
            imports.append(resolved)
    elif module_name:
        imports.append(module_name)

    return imports


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------


def _extract_symbols(root: Node) -> list[str]:
    """Extract top-level symbol names (classes, functions, assignments).

    Only direct children of the module node are considered top-level.

    Args:
        root: The module-level AST node.

    Returns:
        List of symbol name strings.
    """
    symbols: list[str] = []
    for node in root.children:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(_node_text(name_node))
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                symbols.append(_node_text(name_node))
        elif node.type == "expression_statement":
            # Top-level assignments: CONSTANT = 42, __all__ = [...]
            for child in node.children:
                if child.type == "assignment":
                    lhs = child.child_by_field_name("left")
                    if lhs and lhs.type == "identifier":
                        symbols.append(_node_text(lhs))
                    break
        elif node.type == "decorated_definition":
            # @decorator\ndef foo(): ...
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        symbols.append(_node_text(name_node))
    return symbols


# ---------------------------------------------------------------------------
# Python language adapter
# ---------------------------------------------------------------------------


class PythonAdapter(LanguageAdapter):
    """Tree-sitter based Python language adapter."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the adapter.

        Args:
            repo_root: Repository root directory used for relative import resolution.
        """
        self._repo_root = repo_root

    @property
    def language_name(self) -> str:
        """Return the canonical language name."""
        return "python"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".py"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a Python source file and extract a FeatureRecord.

        The tree-sitter CST is discarded before this method returns.

        Args:
            path: Absolute path to the source file.
            source_bytes: Raw file contents.

        Returns:
            FeatureRecord with imports, symbols, pattern_instances, and loc.
        """
        from sdi.parsing._python_patterns import count_loc, extract_pattern_instances

        parser = _get_parser()
        tree = parser.parse(source_bytes)
        root = tree.root_node

        file_pkg = _file_package(path, self._repo_root)
        imports = _extract_imports(root, file_pkg)
        symbols = _extract_symbols(root)
        pattern_instances = extract_pattern_instances(root)
        loc = count_loc(source_bytes)

        # Discard CST: tree and root go out of scope here
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
