"""JavaScript language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from JavaScript source files.
Handles ES module imports, CommonJS require() calls, and dynamic import()
expressions.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_javascript as _tsjs
from tree_sitter import Language, Node, Parser

from sdi.parsing._js_ts_common import (
    _walk_nodes,
    count_loc,
    extract_es_imports,
    extract_pattern_instances,
    extract_reexport_imports,
    extract_require_imports,
    extract_symbols,
    string_fragment,
)
from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across calls in one process.
_PARSER: Parser | None = None


def _get_parser() -> Parser:
    """Return the shared JavaScript parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsjs.language()))
    return _PARSER


def _extract_dynamic_imports(root: Node) -> list[str]:
    """Find dynamic ``import('...')`` expressions and return module paths.

    Matches patterns like ``import('./foo')`` and ``await import('./bar')``.

    Args:
        root: Program root node.

    Returns:
        List of module path strings.
    """
    found: list[str] = []
    for node in _walk_nodes(root):
        if node.type != "call_expression":
            continue
        func = node.child_by_field_name("function")
        if func is None or func.type != "import":
            continue
        args = node.child_by_field_name("arguments")
        if args is None:
            continue
        for child in args.children:
            if child.type == "string":
                path = string_fragment(child)
                if path is not None:
                    found.append(path)
    return found


def _build_imports(root: Node) -> list[str]:
    """Build the full import list for a JavaScript file.

    Combines ES imports, CommonJS require() calls, dynamic import()
    expressions, and re-export sources. Deduplicates while preserving order.

    Args:
        root: Program root node.

    Returns:
        Deduplicated list of import path strings.
    """
    raw: list[str] = []
    raw.extend(extract_es_imports(root))
    raw.extend(extract_require_imports(root))
    raw.extend(_extract_dynamic_imports(root))
    raw.extend(extract_reexport_imports(root))

    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


class JavaScriptAdapter(LanguageAdapter):
    """Tree-sitter based JavaScript language adapter.

    Handles ``.js``, ``.mjs``, and ``.cjs`` files.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize the adapter.

        Args:
            repo_root: Repository root directory.
        """
        self._repo_root = repo_root

    @property
    def language_name(self) -> str:
        """Return the canonical language name."""
        return "javascript"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".js", ".mjs", ".cjs"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a JavaScript source file and extract a FeatureRecord.

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

        imports = _build_imports(root)
        symbols = extract_symbols(root)
        pattern_instances = extract_pattern_instances(root)
        loc = count_loc(source_bytes)

        # Discard CST
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
