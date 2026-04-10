"""Pattern instance extraction for Python AST nodes.

Private module — used only by sdi.parsing.python.
"""

from __future__ import annotations

import hashlib
from typing import Any

from tree_sitter import Node


def _structural_hash(node: Node, max_depth: int = 6) -> str:
    """Hash the structural shape of an AST subtree.

    Only node types are included, not text content. Two structurally
    identical patterns produce the same hash regardless of variable names.

    Args:
        node: Root node of the subtree.
        max_depth: Maximum recursion depth (limits hash input size).

    Returns:
        8-character hex string.
    """
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


def _is_logging_call(node: Node) -> bool:
    """Return True if node is a logging method call.

    Matches patterns like: logging.info(...), logger.warning(...),
    log.debug(...), self.logger.error(...).
    """
    if node.type != "call":
        return False
    func = node.child_by_field_name("function")
    if func is None:
        return False
    # Flatten to text and check common logging patterns
    text = (func.text or b"").decode("utf-8", errors="replace").lower()
    logging_methods = {"debug", "info", "warning", "error", "critical", "exception"}
    # Check if the last attribute matches a logging method
    if "." in text:
        method = text.rsplit(".", 1)[-1]
        return method in logging_methods
    return False


def _is_data_access_call(node: Node) -> bool:
    """Return True if node looks like a data access pattern.

    Matches: db.query(...), session.execute(...), cursor.execute(...),
    .filter(...), .get(...) on ORM-like objects.
    """
    if node.type != "call":
        return False
    func = node.child_by_field_name("function")
    if func is None:
        return False
    text = (func.text or b"").decode("utf-8", errors="replace").lower()
    if "." not in text:
        return False
    method = text.rsplit(".", 1)[-1]
    data_methods = {"query", "execute", "filter", "filter_by", "get", "all", "first", "fetchall", "fetchone"}
    return method in data_methods


def _walk_nodes(node: Node):
    """Yield all descendant nodes via depth-first traversal."""
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def extract_pattern_instances(root: Node) -> list[dict[str, Any]]:
    """Extract pattern instances from the module root node.

    Finds:
    - try/except blocks (category: "error_handling")
    - logging calls (category: "logging")
    - data access calls (category: "data_access")

    Args:
        root: Module-level AST node.

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
        elif node.type == "call":
            if _is_logging_call(node):
                instances.append({
                    "category": "logging",
                    "ast_hash": _structural_hash(node),
                    "location": _location(node),
                })
            elif _is_data_access_call(node):
                instances.append({
                    "category": "data_access",
                    "ast_hash": _structural_hash(node),
                    "location": _location(node),
                })

    return instances


def count_loc(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in Python source.

    Args:
        source_bytes: Raw file bytes.

    Returns:
        Integer line count.
    """
    count = 0
    in_multiline_string = False
    for raw_line in source_bytes.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        # Count triple-quoted string openers/closers (simplified heuristic)
        count += 1
    return count
