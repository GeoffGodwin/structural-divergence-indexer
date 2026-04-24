"""Pattern instance extraction for shell (bash/sh/zsh/ksh) AST nodes.

Private module — used only by sdi.parsing.shell.
"""

from __future__ import annotations

import hashlib
from typing import Any

from tree_sitter import Node

from sdi.parsing._lang_common import _location, _structural_hash, _walk_nodes

_TRAP_SIGNALS: frozenset[str] = frozenset({"ERR", "EXIT", "INT", "TERM", "HUP", "QUIT"})
_LOGGING_COMMANDS: frozenset[str] = frozenset({"echo", "printf", "logger", "tee"})
_BAIL_COMMANDS: frozenset[str] = frozenset({"exit", "return", "false"})
_DATA_ACCESS_COMMANDS: frozenset[str] = frozenset({
    "curl", "wget", "jq", "yq", "psql", "mysql", "mysqldump", "pg_dump",
    "redis-cli", "mongo", "mongosh", "sqlite3", "aws", "gcloud", "kubectl",
    "az", "doctl", "terraform",
})
# Node types whose direct children may include background `&` operators.
_BACKGROUND_CONTAINERS: frozenset[str] = frozenset({
    "program", "compound_statement", "subshell", "function_body", "do_group",
})


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
    return node.children_by_field_name("argument")


def _shell_structural_hash(node: Node, max_depth: int = 6) -> str:
    """Hash an AST subtree, folding command_name into command node hashes.

    For ``command`` nodes, prepends the command name to the serialized
    structure so that ``set -e``, ``trap ERR``, and ``exit 1`` produce
    distinct hashes even though they share the same node type.

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
    return any(
        _node_text(a).startswith("-") and any(c in _node_text(a) for c in "euo")
        for a in args
    )


def _is_trap_error_handling(args: list[Node]) -> bool:
    return bool(args) and any(_node_text(a) in _TRAP_SIGNALS for a in args)


def _is_nonzero_exit_or_return(args: list[Node]) -> bool:
    if not args:
        return False
    text = _node_text(args[0]).strip()
    return text.isdigit() and text != "0"


def _check_list_node(node: Node) -> bool:
    non_extra = [c for c in node.children if not c.is_extra]
    for i, child in enumerate(non_extra):
        if child.type in ("||", "&&") and i + 1 < len(non_extra):
            right = non_extra[i + 1]
            if right.type == "command" and _get_command_name(right) in _BAIL_COMMANDS:
                return True
    return False


def _check_if_exit_or_return(node: Node) -> bool:
    found_then = False
    for child in node.children:
        if child.type == "then":
            found_then = True
            continue
        if found_then and child.type in ("fi", "elif_clause", "else_clause"):
            break
        if found_then and child.type == "command":
            cmd = _get_command_name(child)
            if cmd in {"exit", "return"} and _is_nonzero_exit_or_return(_get_command_args(child)):
                return True
    return False


def _has_test_command_substitution(node: Node) -> bool:
    return any(
        sub is not node and sub.type == "command_substitution"
        for sub in _walk_nodes(node)
    )


def _check_background_children(node: Node) -> list[Node]:
    children = [c for c in node.children if not c.is_extra]
    return [
        children[i - 1]
        for i, child in enumerate(children)
        if child.type == "&" and i > 0 and children[i - 1].type == "command"
    ]


def _is_wide_pipeline(node: Node) -> bool:
    return node.type == "pipeline" and sum(1 for c in node.children if c.type == "|") >= 2


def _is_parallel_xargs(args: list[Node]) -> bool:
    return any(_node_text(a) in ("-P", "--max-procs") for a in args)


def _is_stderr_redirect(node: Node) -> bool:
    return node.type == "redirected_statement" and any(
        c.type == "file_redirect" and ">&2" in _node_text(c)
        for c in node.children
    )


def extract_pattern_instances(root: Node) -> list[dict[str, Any]]:
    """Extract pattern instances from the root of a parsed shell script.

    Detects error_handling, logging, data_access, and async_patterns across
    all four categories using structural AST analysis.

    Args:
        root: Root AST node of the parsed shell script.

    Returns:
        List of pattern instance dicts with keys: category, ast_hash, location.
    """
    instances: list[dict[str, Any]] = []

    def _emit(category: str, hash_val: str, node: Node) -> None:
        instances.append({"category": category, "ast_hash": hash_val, "location": _location(node)})

    for node in _walk_nodes(root):
        ntype = node.type

        if ntype == "command":
            cmd_name = _get_command_name(node)
            args = _get_command_args(node)

            if cmd_name == "set" and _is_set_error_handling(args):
                _emit("error_handling", _shell_structural_hash(node), node)
            elif cmd_name == "trap" and _is_trap_error_handling(args):
                _emit("error_handling", _shell_structural_hash(node), node)
            elif cmd_name in {"exit", "return"} and _is_nonzero_exit_or_return(args):
                _emit("error_handling", _shell_structural_hash(node), node)
            elif cmd_name in _LOGGING_COMMANDS:
                _emit("logging", _shell_structural_hash(node), node)
            elif cmd_name == "wait":
                _emit("async_patterns", _shell_structural_hash(node), node)
            elif cmd_name in ("xargs", "parallel") and _is_parallel_xargs(args):
                _emit("async_patterns", _shell_structural_hash(node), node)
            elif cmd_name in _DATA_ACCESS_COMMANDS:
                _emit("data_access", _shell_structural_hash(node), node)

        elif ntype == "list" and _check_list_node(node):
            _emit("error_handling", _structural_hash(node), node)

        elif ntype == "if_statement" and _check_if_exit_or_return(node):
            _emit("error_handling", _structural_hash(node), node)

        elif ntype == "test_command" and _has_test_command_substitution(node):
            _emit("error_handling", _structural_hash(node), node)

        elif ntype == "redirected_statement" and _is_stderr_redirect(node):
            _emit("logging", _structural_hash(node), node)

        elif ntype in _BACKGROUND_CONTAINERS:
            for cmd_node in _check_background_children(node):
                _emit("async_patterns", _shell_structural_hash(cmd_node), cmd_node)

        elif _is_wide_pipeline(node):
            _emit("async_patterns", _structural_hash(node), node)

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
