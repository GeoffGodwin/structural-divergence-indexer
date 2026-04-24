"""Shell language adapter using tree-sitter-bash.

Handles .sh, .bash, .zsh, .ksh, .dash, .ash files and extensionless
scripts discovered via shebang detection. Extracts:
- imports: static ``source``/``.`` includes resolved to repo-relative paths
- symbols: function names (both ``foo() {}`` and ``function foo {}`` forms)
- pattern_instances: error_handling and logging patterns
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_bash as _tsbash
from tree_sitter import Language, Node, Parser

from sdi.parsing._lang_common import _walk_nodes
from sdi.parsing._shell_patterns import count_loc_shell, extract_pattern_instances
from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord

# Lazily initialized; shared across calls in one process.
_PARSER: Parser | None = None

# Characters that mark a source argument as dynamic (non-static).
_DYNAMIC_CHARS: frozenset[str] = frozenset("$`()*?[] \t")


def _get_parser() -> Parser:
    """Return the shared shell parser, initializing on first call."""
    global _PARSER
    if _PARSER is None:
        _PARSER = Parser(Language(_tsbash.language()))
    return _PARSER


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return (node.text or b"").decode("utf-8", errors="replace")


def _get_command_name(node: Node) -> str:
    """Return the command name text from a command node."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return ""
    return _node_text(name_node).strip()


def _is_static_literal(arg_node: Node) -> bool:
    """Return True if the argument node is a static (non-dynamic) word.

    Rejects any argument whose type is not ``word`` or whose text contains
    dynamic shell characters ($, backtick, parentheses, glob chars, spaces).
    """
    if arg_node.type != "word":
        return False
    text = _node_text(arg_node)
    return not any(c in _DYNAMIC_CHARS for c in text)


def _resolve_source_path(
    literal: str,
    file_path: Path,
    repo_root: Path,
) -> str | None:
    """Resolve a static source/. argument to a repo-relative POSIX path.

    Args:
        literal: The literal string from the source argument.
        file_path: Absolute path of the importing script.
        repo_root: Repository root directory.

    Returns:
        Repo-relative POSIX path string, or None if resolution fails.
    """
    try:
        if literal.startswith("/"):
            resolved = Path(literal).resolve()
        else:
            resolved = (file_path.parent / literal).resolve()
        return resolved.relative_to(repo_root).as_posix()
    except (ValueError, OSError):
        return None


def _extract_imports(root: Node, file_path: Path, repo_root: Path) -> list[str]:
    """Extract static source/. includes and resolve to repo-relative paths.

    Dynamic forms (containing $, backticks, substitutions, etc.) are
    silently ignored. Only single-argument static literals are resolved.

    Args:
        root: Root AST node.
        file_path: Absolute path of the script being parsed.
        repo_root: Repository root directory.

    Returns:
        Deduplicated list of repo-relative POSIX path strings.
    """
    imports: list[str] = []
    seen: set[str] = set()

    for node in _walk_nodes(root):
        if node.type != "command":
            continue
        cmd_name = _get_command_name(node)
        if cmd_name not in ("source", "."):
            continue
        args = node.children_by_field_name("argument")
        if len(args) != 1:
            continue
        arg_node = args[0]
        if not _is_static_literal(arg_node):
            continue
        literal = _node_text(arg_node)
        resolved = _resolve_source_path(literal, file_path, repo_root)
        if resolved is not None and resolved not in seen:
            seen.add(resolved)
            imports.append(resolved)

    return imports


def _extract_symbols(root: Node) -> list[str]:
    """Extract function names from shell function definitions.

    Handles both declaration forms:
    - ``foo() { ... }``
    - ``function foo { ... }``

    Both parse to ``function_definition`` nodes with a ``name`` field.

    Args:
        root: Root AST node.

    Returns:
        List of function name strings.
    """
    symbols: list[str] = []
    for node in _walk_nodes(root):
        if node.type != "function_definition":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            name = _node_text(name_node).strip()
            if name:
                symbols.append(name)
    return symbols


class ShellAdapter(LanguageAdapter):
    """Tree-sitter based shell language adapter.

    Supports Bash, sh, zsh, ksh, dash, and ash scripts.
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
        return "shell"

    @property
    def file_extensions(self) -> frozenset[str]:
        """Return supported file extensions."""
        return frozenset({".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash"})

    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse a shell script and extract a FeatureRecord.

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

        imports = _extract_imports(root, path, self._repo_root)
        symbols = _extract_symbols(root)
        pattern_instances = extract_pattern_instances(root)
        loc = count_loc_shell(source_bytes)

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
