"""Pattern instance extraction for shell (bash/sh/zsh/ksh) AST nodes.

Private module — used only by sdi.parsing.shell.
"""

from __future__ import annotations

import hashlib
from typing import Any

from tree_sitter import Node

from sdi.parsing._lang_common import _location, _structural_hash, _walk_nodes

# Signal names that indicate error-handling trap handlers.
_TRAP_SIGNALS: frozenset[str] = frozenset({"ERR", "EXIT", "INT", "TERM", "HUP"})

# Command names that constitute logging patterns.
_LOGGING_COMMANDS: frozenset[str] = frozenset({"echo", "printf", "logger", "tee"})

# Command names on the right side of || / && that signal error handling.
_BAIL_COMMANDS: frozenset[str] = frozenset({"exit", "return", "false"})


def _node_text(node: Node) -> str:
    """Decode a node's source text as UTF-8."""
    return (node.text or b"").decode("utf-8", errors="replace")


def _get_command_name(node: Node) -> str:
    """Return the command name text from a command node."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return ""
    return _node_text(name_node).strip()


def _get_command_args(node: Node) -> list[Node]:
    """Return argument nodes from a command node."""
    return node.children_by_field_name("argument")


def _shell_structural_hash(node: Node, max_depth: int = 6) -> str:
    """Hash an AST subtree, folding command_name into command node hashes.

    For ``command`` nodes, prepends the command name to the serialized
    structure so that ``set -e``, ``trap ERR``, and ``exit 1`` produce
    distinct hashes even though they share the same node type.

    For all other node types, delegates to _lang_common._structural_hash.

    Args:
        node: Root node of the subtree.
        max_depth: Maximum recursion depth.

    Returns:
        8-character hex string.
    """
    if node.type != "command":
        return _structural_hash(node, max_depth)

    cmd_name = _get_command_name(node)

    def _serialize(n: Node, depth: int) -> str:
        if depth == 0:
            return n.type
        children = [_serialize(c, depth - 1) for c in n.children if not c.is_extra]
        return f"{n.type}({','.join(children)})"

    serialized = f"cmd:{cmd_name}:{_serialize(node, max_depth)}"
    return hashlib.sha256(serialized.encode()).hexdigest()[:8]


def _is_set_error_handling(args: list[Node]) -> bool:
    """Return True if a ``set`` command's args indicate error-handling mode."""
    for arg in args:
        text = _node_text(arg)
        if text.startswith("-") and ("e" in text or "u" in text or "o" in text):
            return True
    return False


def _is_trap_error_handling(args: list[Node]) -> bool:
    """Return True if a ``trap`` command targets an error-related signal."""
    if not args:
        return False
    last_text = _node_text(args[-1])
    return last_text in _TRAP_SIGNALS


def _is_nonzero_exit_or_return(args: list[Node]) -> bool:
    """Return True if exit/return uses a non-zero numeric literal."""
    if not args:
        return False
    text = _node_text(args[0]).strip()
    return text.isdigit() and text != "0"


def _check_list_node(node: Node) -> bool:
    """Return True if a list (||/&&) node's right side bails on error."""
    non_extra = [c for c in node.children if not c.is_extra]
    for i, child in enumerate(non_extra):
        if child.type in ("||", "&&") and i + 1 < len(non_extra):
            right = non_extra[i + 1]
            if right.type == "command":
                return _get_command_name(right) in _BAIL_COMMANDS
    return False


def extract_pattern_instances(root: Node) -> list[dict[str, Any]]:
    """Extract pattern instances from the root of a parsed shell script.

    Detects:
    - error_handling: set -e/u/o, trap ERR/EXIT/…, exit/return non-zero,
      list nodes (||/&&) whose right side is exit/return/false.
    - logging: echo, printf, logger, tee commands.

    Args:
        root: Root AST node of the parsed shell script.

    Returns:
        List of pattern instance dicts with keys: category, ast_hash, location.
    """
    instances: list[dict[str, Any]] = []

    for node in _walk_nodes(root):
        if node.type == "command":
            cmd_name = _get_command_name(node)
            args = _get_command_args(node)

            if cmd_name == "set" and _is_set_error_handling(args):
                instances.append({
                    "category": "error_handling",
                    "ast_hash": _shell_structural_hash(node),
                    "location": _location(node),
                })
            elif cmd_name == "trap" and _is_trap_error_handling(args):
                instances.append({
                    "category": "error_handling",
                    "ast_hash": _shell_structural_hash(node),
                    "location": _location(node),
                })
            elif cmd_name in {"exit", "return"} and _is_nonzero_exit_or_return(args):
                instances.append({
                    "category": "error_handling",
                    "ast_hash": _shell_structural_hash(node),
                    "location": _location(node),
                })
            elif cmd_name in _LOGGING_COMMANDS:
                instances.append({
                    "category": "logging",
                    "ast_hash": _shell_structural_hash(node),
                    "location": _location(node),
                })

        elif node.type == "list" and _check_list_node(node):
            instances.append({
                "category": "error_handling",
                "ast_hash": _structural_hash(node),
                "location": _location(node),
            })

    return instances


def count_loc_shell(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in a shell script.

    Args:
        source_bytes: Raw file bytes.

    Returns:
        Integer line count.
    """
    count = 0
    for raw_line in source_bytes.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        count += 1
    return count
