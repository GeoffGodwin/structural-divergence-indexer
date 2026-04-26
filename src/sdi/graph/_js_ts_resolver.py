"""TypeScript / JavaScript import resolution helpers.

Extracted from builder.py to keep that module under the 300-line ceiling.
All public names are re-exported by builder.py for backward compatibility.
"""

from __future__ import annotations

import json
import logging
import posixpath
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_JS_TS_EXTS: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
_JS_TS_LANGS: frozenset[str] = frozenset({"typescript", "javascript"})


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
        import_str = import_str[len("type:"):]
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
