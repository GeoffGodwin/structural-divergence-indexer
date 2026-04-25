"""Dependency graph construction from FeatureRecord objects.

Builds a directed igraph.Graph where nodes are source files and edges
represent import dependencies. Only intra-project imports create edges;
external (stdlib, third-party) imports are silently dropped.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

try:
    import igraph
except ImportError:
    print(
        "[error] igraph is required for graph construction. Install with: pip install igraph",
        file=sys.stderr,
    )
    raise

if TYPE_CHECKING:
    from sdi.config import SDIConfig
    from sdi.parsing import FeatureRecord

logger = logging.getLogger(__name__)


def _file_path_to_module_key(file_path: str) -> str | None:
    """Convert a relative file path to a canonical Python module key.

    Args:
        file_path: Relative path to source file (forward or back slashes).

    Returns:
        Dotted module key string, or None for non-Python files.

    Examples:
        "models/user.py"        → "models.user"
        "models/__init__.py"    → "models"
        "src/sdi/config.py"     → "sdi.config"
        "main.py"               → "main"

    Note:
        Assumes `src/` is a build-layout prefix with no corresponding importable
        package. A project with a real top-level package named `src` would have
        its module keys silently truncated.
    """
    path = file_path.replace("\\", "/")

    if not path.endswith(".py"):
        return None

    path = path[:-3]  # strip .py

    # "foo/__init__" → "foo" (package init represents the package itself)
    if path.endswith("/__init__"):
        path = path[:-9]

    module_key = path.replace("/", ".")

    # Strip leading "src." for src-layout projects
    if module_key.startswith("src."):
        module_key = module_key[4:]

    return module_key


def _build_module_map(file_paths: set[str]) -> dict[str, str]:
    """Build a reverse mapping from module key to file path.

    Args:
        file_paths: Set of relative file path strings from FeatureRecords.

    Returns:
        Dict mapping canonical module key → file path.
        Non-Python files are omitted.
    """
    module_map: dict[str, str] = {}
    for fp in file_paths:
        key = _file_path_to_module_key(fp)
        if key is not None:
            if key in module_map:
                logger.debug(
                    "Module key collision: %r maps to both %r and %r — keeping first",
                    key,
                    module_map[key],
                    fp,
                )
            else:
                module_map[key] = fp
    return module_map


def _resolve_import(import_str: str, module_map: dict[str, str]) -> str | None:
    """Resolve an import string to a file path using the module map.

    Tries exact match first, then longest-suffix match. Suffix matching
    handles cases where the imported module path includes a package prefix
    that is not part of the file system layout (e.g., the import uses the
    top-level package name but the repo root is the package directory).

    Args:
        import_str: Dotted module path string from FeatureRecord.imports.
        module_map: Dict of module_key → file_path for known project files.

    Returns:
        Matching file path string, or None if no intra-project match.
    """
    # Fast path: exact match
    if import_str in module_map:
        return module_map[import_str]

    # Suffix match: find all keys that are a proper dotted suffix of import_str
    best_file: str | None = None
    best_key_len = 0

    for module_key, file_path in module_map.items():
        if import_str.endswith("." + module_key):
            if len(module_key) > best_key_len:
                best_file = file_path
                best_key_len = len(module_key)

    return best_file


def build_dependency_graph(
    records: list[FeatureRecord],
    config: SDIConfig,
) -> tuple[igraph.Graph, dict[str, int]]:
    """Build a directed dependency graph from parsed FeatureRecord objects.

    Nodes represent source files. Directed edges represent import dependencies
    (source → imported). External and unresolvable imports are silently dropped.
    Self-imports are counted but not added as edges.

    The graph is deterministic: same input always produces the same vertex
    ordering and edge list.

    Args:
        records: Parsed feature records from Stage 1 (parsing).
        config: SDI configuration (controls weighted_edges toggle).

    Returns:
        Tuple of (graph, metadata) where:
            graph: igraph.Graph with vertex attribute "name" = file_path.
            metadata: Dict with keys "unresolved_count" and "self_import_count".
    """
    weighted = config.boundaries.weighted_edges

    # Sort file paths for deterministic vertex ordering
    sorted_paths = sorted(r.file_path for r in records)
    path_to_id: dict[str, int] = {fp: i for i, fp in enumerate(sorted_paths)}

    g = igraph.Graph(n=len(sorted_paths), directed=True)
    if sorted_paths:
        g.vs["name"] = sorted_paths

    if not records:
        return g, {"unresolved_count": 0, "self_import_count": 0}

    # Build module-key → file-path reverse lookup
    module_map = _build_module_map(set(path_to_id.keys()))

    # Collect raw (src_id, tgt_id) pairs (with duplicates for weighting)
    unresolved_count = 0
    self_import_count = 0
    raw_edges: list[tuple[int, int]] = []

    # Process records in sorted order for determinism
    for record in sorted(records, key=lambda r: r.file_path):
        src_id = path_to_id[record.file_path]

        for import_str in record.imports:
            target_path = _resolve_import(import_str, module_map)

            if target_path is None:
                unresolved_count += 1
                logger.debug("Unresolved import %r in %r", import_str, record.file_path)
                continue

            tgt_id = path_to_id[target_path]

            if tgt_id == src_id:
                self_import_count += 1
                logger.debug("Self-import %r skipped in %r", import_str, record.file_path)
                continue

            raw_edges.append((src_id, tgt_id))

    # Build final edge list (deduplicated for unweighted; aggregated for weighted)
    if weighted:
        edge_weight_map: dict[tuple[int, int], int] = {}
        for edge in raw_edges:
            edge_weight_map[edge] = edge_weight_map.get(edge, 0) + 1
        final_edges = list(edge_weight_map.keys())
        g.add_edges(final_edges)
        g.es["weight"] = [edge_weight_map[e] for e in final_edges]
    else:
        # Deduplicate while preserving first-encounter order (via dict keys)
        final_edges = list(dict.fromkeys(raw_edges))
        g.add_edges(final_edges)

    metadata: dict[str, int] = {
        "unresolved_count": unresolved_count,
        "self_import_count": self_import_count,
    }
    return g, metadata
