"""Common AST utility functions shared across language adapters.

Private module — used by sdi.parsing adapters and sdi.parsing._js_ts_common.
These four functions are language-agnostic: they operate on tree-sitter Node
objects and raw source bytes with no language-specific assumptions.
"""

from __future__ import annotations

import hashlib

from tree_sitter import Node


def _structural_hash(node: Node, max_depth: int = 6) -> str:
    """Hash the structural shape of an AST subtree (type-only, not text).

    Args:
        node: Root node of the subtree.
        max_depth: Maximum recursion depth.

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


def _walk_nodes(node: Node):
    """Yield all descendant nodes via depth-first traversal."""
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def count_loc(source_bytes: bytes) -> int:
    """Count non-blank, non-comment lines in C-style source.

    Handles ``//`` single-line comments and ``/* ... */`` block comments.
    Language-agnostic: applies to Go, Java, Rust, JS, and TS source files.

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
