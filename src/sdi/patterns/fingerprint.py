"""Pattern fingerprinting: structural hash computation from AST subtree descriptors.

Normalizes AST subtrees by:
- Keeping node type names
- Replacing identifier node types with "_ID_"
- Replacing literal node types with a type token ("_STR_", "_INT_", "_FLOAT_", "_BOOL_", "_NONE_")

Two structurally equivalent subtrees (same node types, different identifiers or literals)
produce the same hash. This is the canonical representation used in PatternCatalog.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

# Node types that are identifiers — normalized to "_ID_" in the structural serialization.
_IDENTIFIER_TYPES: frozenset[str] = frozenset({"identifier", "name", "attribute"})

# Exact node type → normalization token for literals.
_LITERAL_TOKENS: dict[str, str] = {
    "string": "_STR_",
    "string_content": "_STR_",
    "integer": "_INT_",
    "float": "_FLOAT_",
    "true": "_BOOL_",
    "false": "_BOOL_",
    "none": "_NONE_",
    "null": "_NONE_",
}


@dataclass(frozen=True)
class PatternFingerprint:
    """A structural pattern shape defined by its normalized AST hash.

    Equality and hashing are based solely on structural_hash, so two fingerprints
    with the same hash represent the same structural shape regardless of the source
    identifiers or literals.

    Args:
        category: Pattern category name (e.g., "error_handling").
        structural_hash: 16-character hex string of the normalized shape.
        node_count: Number of AST nodes in the subtree (used for min_pattern_nodes
            filtering). May be 0 when created from a pre-computed hash.
    """

    category: str
    structural_hash: str
    node_count: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PatternFingerprint):
            return NotImplemented
        return self.structural_hash == other.structural_hash

    def __hash__(self) -> int:
        return hash(self.structural_hash)


def _count_nodes(descriptor: dict[str, Any]) -> int:
    """Count total nodes in an AST descriptor tree.

    Args:
        descriptor: Dict with optional 'children' key containing sub-descriptors.

    Returns:
        Total node count including root and all descendants.
    """
    count = 1
    for child in descriptor.get("children", []):
        count += _count_nodes(child)
    return count


def _normalize_serialize(descriptor: dict[str, Any]) -> str:
    """Serialize a descriptor tree with structural normalization.

    Identifier node types are replaced with "_ID_". Literal node types are
    replaced with their type token ("_STR_", "_INT_", etc.). Only structure
    (node type + children) is serialized — text content is ignored.

    Args:
        descriptor: Dict with keys 'type', optional 'text', optional 'children'.

    Returns:
        Normalized string representation of the subtree.
    """
    node_type = descriptor.get("type", "unknown")

    if node_type in _IDENTIFIER_TYPES:
        return "_ID_"

    token = _LITERAL_TOKENS.get(node_type)
    if token is not None:
        return token

    children = descriptor.get("children", [])
    if not children:
        return node_type

    child_parts = ",".join(_normalize_serialize(c) for c in children)
    return f"{node_type}({child_parts})"


def compute_structural_hash(
    descriptor: dict[str, Any],
    min_nodes: int = 1,
) -> tuple[str, int] | None:
    """Compute a normalized structural hash for an AST descriptor.

    Normalizes identifier and literal nodes, then hashes the structural shape.

    Args:
        descriptor: Dict with keys 'type', optional 'text', optional 'children'.
            Children are recursively processed.
        min_nodes: If the descriptor has fewer nodes than this threshold, return
            None to indicate the pattern should be filtered out.

    Returns:
        (hash_hex_16, node_count) tuple, or None if below min_nodes or invalid.
    """
    if not descriptor or "type" not in descriptor:
        return None

    node_count = _count_nodes(descriptor)
    if node_count < min_nodes:
        return None

    serialized = _normalize_serialize(descriptor)
    hash_hex = hashlib.sha256(serialized.encode()).hexdigest()[:16]
    return hash_hex, node_count


def fingerprint_from_instance(
    instance: dict[str, Any],
    min_nodes: int = 1,
) -> PatternFingerprint | None:
    """Create a PatternFingerprint from a pre-computed pattern instance dict.

    Used when pattern_instances have already been computed by the parsing stage.
    The ast_hash in the instance is used directly as the structural_hash.

    Args:
        instance: Dict with keys 'category', 'ast_hash', 'location', and
            optional 'node_count'.
        min_nodes: If instance has an explicit 'node_count' below this threshold,
            returns None (filtered out). Absent node_count always passes.

    Returns:
        PatternFingerprint, or None if filtered by min_nodes.
    """
    category = instance.get("category", "")
    ast_hash = instance.get("ast_hash", "")
    node_count = instance.get("node_count")  # None if absent

    if node_count is not None and node_count < min_nodes:
        return None

    return PatternFingerprint(
        category=category,
        structural_hash=ast_hash,
        node_count=node_count if node_count is not None else 0,
    )
