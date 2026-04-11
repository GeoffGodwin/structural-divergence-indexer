"""TypeScript language adapter using tree-sitter.

Extracts imports, symbols, and pattern instances from TypeScript source files.
Type-only imports (``import type { Foo } from './bar'``) are included in
``FeatureRecord.imports`` with a ``type:`` prefix to annotate them as
type-dependencies (see Seeds Forward convention in CLAUDE.md M03).
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_typescript as _tsts
from tree_sitter import Language, Parser

from sdi.parsing._js_ts_common import (
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

# Lazily initialized parsers; shared across calls in one process.
_TS_PARSER: Parser | None = None
_TSX_PARSER: Parser | None = None


def _get_ts_parser() -> Parser:
    """Return the shared TypeScript parser, initializing on first call."""
    global _TS_PARSER
    if _TS_PARSER is None:
        _TS_PARSER = Parser(Language(_tsts.language_typescript()))
    return _TS_PARSER


def _get_tsx_parser() -> Parser:
    """Return the shared TSX parser, initializing on first call."""
    global _TSX_PARSER
    if _TSX_PARSER is None:
        _TSX_PARSER = Parser(Language(_tsts.language_tsx()))
    return _TSX_PARSER


def _extract_type_only_imports(root) -> list[str]:
    """Extract type-only import paths, annotated with ``type:`` prefix.

    Covers ``import type { Foo } from './bar'``.

    Args:
        root: Program root node.

    Returns:
        List of strings like ``['type:./bar']``.
    """
    found: list[str] = []
    for child in root.children:
        if child.type != "import_statement":
            continue
        has_type_keyword = any(c.type == "type" for c in child.children)
        if not has_type_keyword:
            continue
        for c in child.children:
            if c.type == "string":
                path = string_fragment(c)
                if path is not None:
                    found.append(f"type:{path}")
    return found


def _build_imports(root) -> list[str]:
    """Build the full import list for a TypeScript file.

    Combines ES imports, type-only imports (prefixed ``type:``),
    CommonJS require() calls, and re-export sources.
    Deduplicates while preserving order.

    Args:
        root: Program root node.

    Returns:
        Deduplicated list of import path strings.
    """
    raw: list[str] = []
    raw.extend(extract_es_imports(root))
    raw.extend(_extract_type_only_imports(root))
    raw.extend(extract_require_imports(root))
    raw.extend(extract_reexport_imports(root))

    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


class TypeScriptAdapter(LanguageAdapter):
    """Tree-sitter based TypeScript language adapter.

    Handles both ``.ts`` and ``.tsx`` files.
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
        return "typescript"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".ts", ".tsx"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a TypeScript source file and extract a FeatureRecord.

        The tree-sitter CST is discarded before this method returns.

        Args:
            path: Absolute path to the source file.
            source_bytes: Raw file contents.

        Returns:
            FeatureRecord with imports, symbols, pattern_instances, and loc.
        """
        parser = _get_tsx_parser() if path.suffix == ".tsx" else _get_ts_parser()
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
