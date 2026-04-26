"""Dependency graph construction from FeatureRecord objects.

Builds a directed igraph.Graph where nodes are source files and edges
represent import dependencies. Only intra-project imports create edges;
external (stdlib, third-party) imports are silently dropped.

Resolution is language-dispatched:
- Shell: direct path lookup + bounded extension fallback (.sh, .bash)
- TypeScript/JavaScript: path-based resolution (relative paths, tsconfig
  path aliases, extension and index fallbacks)
- Python (default): canonical dotted module key resolution
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

try:
    import igraph
except ImportError:
    print(
        "[error] igraph is required for graph construction. Install with: pip install igraph",
        file=sys.stderr,
    )
    raise

from sdi.graph._js_ts_resolver import (
    _JS_TS_LANGS,
    _build_js_path_set,
    _is_js_ts_file,
    _load_ts_path_aliases,
    _normalize_js_path,
    _resolve_js_import,
)

if TYPE_CHECKING:
    from sdi.config import SDIConfig
    from sdi.parsing import FeatureRecord

logger = logging.getLogger(__name__)

_SHELL_LANGS: frozenset[str] = frozenset({"shell"})

# Intentionally a tuple, not a frozenset — order determines fallback preference.
# .sh is checked before .bash. Do NOT convert to a frozenset; frozenset
# iteration order is non-deterministic in CPython and would break the
# same-input → same-output reproducibility guarantee.
_SHELL_EXTENSIONS_FOR_FALLBACK: tuple[str, ...] = (".sh", ".bash")

# Extensions that signal the literal already names a specific shell dialect;
# extension fallback is skipped when the import string ends in any of these.
_KNOWN_SHELL_EXTS: frozenset[str] = frozenset({".sh", ".bash", ".zsh", ".ksh", ".dash", ".ash"})


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


def _resolve_shell_import(import_str: str, path_set: frozenset[str]) -> str | None:
    """Resolve a shell source/. import string to a project file path.

    The shell adapter pre-resolves source arguments against the importing
    script's directory, producing repo-relative POSIX paths. This function
    performs lookup only — no path math.

    _SHELL_EXTENSIONS_FOR_FALLBACK is intentionally a tuple (not a set).
    Order is significant: .sh is checked before .bash. Do NOT convert to a
    frozenset — frozenset iteration order is non-deterministic in CPython and
    would break the same-input → same-output reproducibility guarantee.

    Args:
        import_str: Repo-relative POSIX path from FeatureRecord.imports.
        path_set: Full set of repo-relative file paths (all languages).

    Returns:
        Matching repo-relative file path, or None if not resolved.
    """
    # Fast path: exact match (literal already carries the right extension)
    if import_str in path_set:
        return import_str

    # Extension fallback: only when the literal does not already end in a
    # known shell dialect extension. E.g. "common.zsh" has a known extension
    # and is not retried as "common.zsh.sh".
    if not any(import_str.endswith(ext) for ext in _KNOWN_SHELL_EXTS):
        for ext in _SHELL_EXTENSIONS_FOR_FALLBACK:
            candidate = import_str + ext
            if candidate in path_set:
                return candidate

    return None


def build_dependency_graph(
    records: list[FeatureRecord],
    config: SDIConfig,
    repo_root: Path | None = None,
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
        repo_root: Repository root used to load TS path aliases from
            tsconfig.json or jsconfig.json. If None, JS/TS imports are
            resolved without alias support — relative-path imports still
            work, but ``@/foo``-style aliased imports will not.

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

    # Build language-specific lookups
    module_map = _build_module_map(set(path_to_id.keys()))
    js_path_set = _build_js_path_set(set(path_to_id.keys()))
    js_norm_to_original: dict[str, str] = {_normalize_js_path(fp): fp for fp in path_to_id if _is_js_ts_file(fp)}
    aliases = _load_ts_path_aliases(repo_root) if repo_root is not None else []
    # Full path set for shell resolution — all languages, no filtering.
    # A bash script sourcing a co-located .env-style file that happens to be
    # tracked as a Python record is a legitimate cross-language edge.
    shell_path_set: frozenset[str] = frozenset(path_to_id.keys())

    # Collect raw (src_id, tgt_id) pairs (with duplicates for weighting)
    unresolved_count = 0
    self_import_count = 0
    raw_edges: list[tuple[int, int]] = []

    # Process records in sorted order for determinism
    for record in sorted(records, key=lambda r: r.file_path):
        src_id = path_to_id[record.file_path]
        is_shell = record.language in _SHELL_LANGS
        is_js_ts = record.language in _JS_TS_LANGS

        for import_str in record.imports:
            if is_shell:
                target_path = _resolve_shell_import(import_str, shell_path_set)
            elif is_js_ts:
                resolved_norm = _resolve_js_import(import_str, record.file_path, js_path_set, aliases)
                target_path = js_norm_to_original.get(resolved_norm) if resolved_norm is not None else None
            else:
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
