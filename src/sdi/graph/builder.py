"""Dependency graph construction from FeatureRecord objects.

Builds a directed igraph.Graph where nodes are source files and edges
represent import dependencies. Only intra-project imports create edges;
external (stdlib, third-party) imports are silently dropped.

Resolution is language-dispatched: Python imports use canonical dotted
module keys; TypeScript/JavaScript imports use path-based resolution
(relative paths, tsconfig path aliases, extension and index fallbacks).
"""

from __future__ import annotations

import json
import logging
import posixpath
import re
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

if TYPE_CHECKING:
    from sdi.config import SDIConfig
    from sdi.parsing import FeatureRecord

logger = logging.getLogger(__name__)

_JS_TS_EXTS: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
_JS_TS_LANGS: frozenset[str] = frozenset({"typescript", "javascript"})


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


def _is_js_ts_file(file_path: str) -> bool:
    """Return True if the path has a TS/JS source extension."""
    return any(file_path.endswith(ext) for ext in _JS_TS_EXTS)


def _normalize_js_path(file_path: str) -> str:
    """Normalize a JS/TS file path: forward slashes, no leading ``./``."""
    p = file_path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _build_js_path_set(file_paths: set[str]) -> set[str]:
    """Build the set of normalized TS/JS file paths in the project."""
    return {_normalize_js_path(fp) for fp in file_paths if _is_js_ts_file(fp)}


_JSONC_LINE_COMMENT = re.compile(r"//[^\n]*")
_JSONC_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_JSONC_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _strip_jsonc(text: str) -> str:
    """Strip JSONC artifacts (line/block comments and trailing commas).

    tsconfig.json commonly contains comments. Strict ``json`` cannot parse
    these; this routine produces parseable JSON good enough for the
    ``compilerOptions.paths`` field. String contents are not protected from
    comment-like substrings — acceptable since paths/baseUrl are simple
    identifiers in practice.
    """
    text = _JSONC_BLOCK_COMMENT.sub("", text)
    text = _JSONC_LINE_COMMENT.sub("", text)
    text = _JSONC_TRAILING_COMMA.sub(r"\1", text)
    return text


def _load_ts_path_aliases(repo_root: Path) -> list[tuple[str, list[str]]]:
    """Load ``compilerOptions.paths`` from tsconfig.json or jsconfig.json.

    Targets are resolved against ``baseUrl`` (default: ``.``) and normalized
    to repo-relative POSIX paths. Aliases may contain a single ``*`` wildcard.

    Returns:
        List of ``(alias_pattern, resolved_target_patterns)`` tuples.
        Empty list if no config is present or parseable.
    """
    aliases: list[tuple[str, list[str]]] = []
    for fname in ("tsconfig.json", "jsconfig.json"):
        cfg_path = repo_root / fname
        if not cfg_path.is_file():
            continue
        try:
            text = cfg_path.read_text(encoding="utf-8")
            data = json.loads(_strip_jsonc(text))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Failed to parse %s: %s", cfg_path, exc)
            continue
        opts = data.get("compilerOptions") or {}
        paths = opts.get("paths") or {}
        base_url = opts.get("baseUrl") or "."
        for pattern, targets in paths.items():
            if not isinstance(targets, list):
                continue
            resolved = []
            for t in targets:
                if not isinstance(t, str):
                    continue
                joined = posixpath.normpath(posixpath.join(base_url, t))
                resolved.append(joined)
            if resolved:
                aliases.append((pattern, resolved))
        if aliases:
            return aliases
    return aliases


def _match_alias(import_str: str, pattern: str) -> str | None:
    """Match ``import_str`` against a TS path alias pattern.

    Returns the wildcard-captured substring if matched; an empty string if
    matched and the pattern has no ``*``; ``None`` if no match.
    """
    if "*" not in pattern:
        return "" if import_str == pattern else None
    prefix, _, suffix = pattern.partition("*")
    if not import_str.startswith(prefix):
        return None
    if suffix and not import_str.endswith(suffix):
        return None
    if len(import_str) < len(prefix) + len(suffix):
        return None
    end = len(import_str) - len(suffix) if suffix else len(import_str)
    return import_str[len(prefix) : end]


def _expand_alias_candidates(import_str: str, aliases: list[tuple[str, list[str]]]) -> list[str] | None:
    """Expand an import string through alias patterns into target candidates.

    Returns ``None`` when no alias matches (caller should treat the import as
    non-aliased). Returns a list of candidate paths otherwise — these are
    repo-relative POSIX paths to attempt resolution against.
    """
    for pattern, targets in aliases:
        captured = _match_alias(import_str, pattern)
        if captured is None:
            continue
        candidates: list[str] = []
        for target in targets:
            if "*" in target:
                candidates.append(target.replace("*", captured))
            else:
                candidates.append(target)
        return candidates
    return None


def _try_extensions_and_index(path: str, js_path_set: set[str]) -> str | None:
    """Probe the JS/TS path set for ``path`` with extension/index fallbacks.

    Resolution order mirrors typical TS/Node module resolution:
      1. Exact match
      2. ``.js``/``.mjs`` import → corresponding ``.ts``/``.tsx`` source (TS rewrite)
      3. Append common source extensions
      4. Treat as directory and probe ``index.<ext>``
    """
    path = _normalize_js_path(path)
    if path in js_path_set:
        return path

    # TS rewrite: foo.js / foo.mjs (ESM-spec import) → foo.ts / foo.tsx
    for js_ext, replacements in (
        (".js", (".ts", ".tsx")),
        (".mjs", (".mts",)),
        (".cjs", (".cts",)),
    ):
        if path.endswith(js_ext):
            stem = path[: -len(js_ext)]
            for ext in replacements:
                cand = stem + ext
                if cand in js_path_set:
                    return cand

    for ext in _JS_TS_EXTS:
        cand = path + ext
        if cand in js_path_set:
            return cand

    for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        cand = f"{path}/index{ext}" if path else f"index{ext}"
        if cand in js_path_set:
            return cand

    return None


def _resolve_js_import(
    import_str: str,
    source_file_path: str,
    js_path_set: set[str],
    aliases: list[tuple[str, list[str]]],
) -> str | None:
    """Resolve a single TS/JS import string to a project file path.

    Args:
        import_str: Raw import path from FeatureRecord.imports. May carry a
            ``type:`` prefix for TypeScript type-only imports.
        source_file_path: Repo-relative path of the importing file.
        js_path_set: Set of normalized TS/JS file paths in the project.
        aliases: TS path aliases from ``_load_ts_path_aliases``.

    Returns:
        Repo-relative path of the resolved target, or ``None`` if the import
        is external (bare specifier), unresolvable, or points at a non-source
        asset (.css, .json, etc.).
    """
    if import_str.startswith("type:"):
        import_str = import_str[len("type:") :]
    if not import_str:
        return None

    aliased = _expand_alias_candidates(import_str, aliases)
    if aliased is not None:
        candidates = aliased
    else:
        candidates = [import_str]

    source_dir = posixpath.dirname(_normalize_js_path(source_file_path))

    for candidate in candidates:
        # Bare specifier (npm package etc.) — only relative or absolute paths
        # become resolution targets. Aliased candidates were already rewritten
        # to project-relative paths, so they fall through here.
        is_relative = candidate.startswith("./") or candidate.startswith("../")
        is_absolute = candidate.startswith("/")
        is_aliased = aliased is not None
        if not (is_relative or is_absolute or is_aliased):
            continue

        if is_absolute:
            normalized = candidate.lstrip("/")
        elif is_relative:
            normalized = posixpath.normpath(posixpath.join(source_dir, candidate) if source_dir else candidate)
        else:
            # Aliased candidate is already repo-relative
            normalized = posixpath.normpath(candidate)

        # Drop non-source assets (CSS, JSON, images, etc.)
        ext = posixpath.splitext(normalized)[1]
        if ext and ext not in _JS_TS_EXTS and ext not in (".js", ".mjs", ".cjs"):
            continue

        resolved = _try_extensions_and_index(normalized, js_path_set)
        if resolved is not None:
            return resolved

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
    # Map normalized JS/TS path → original path (for vertex id lookup)
    js_norm_to_original: dict[str, str] = {_normalize_js_path(fp): fp for fp in path_to_id if _is_js_ts_file(fp)}
    aliases = _load_ts_path_aliases(repo_root) if repo_root is not None else []

    # Collect raw (src_id, tgt_id) pairs (with duplicates for weighting)
    unresolved_count = 0
    self_import_count = 0
    raw_edges: list[tuple[int, int]] = []

    # Process records in sorted order for determinism
    for record in sorted(records, key=lambda r: r.file_path):
        src_id = path_to_id[record.file_path]
        is_js_ts = record.language in _JS_TS_LANGS

        for import_str in record.imports:
            if is_js_ts:
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
