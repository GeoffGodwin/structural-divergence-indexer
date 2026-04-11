"""File discovery with .gitignore filtering and language detection."""

from __future__ import annotations

from pathlib import Path

import pathspec

# Extension → language name mapping
_EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
}


def detect_language(path: Path) -> str | None:
    """Return the language name for a file path, or None if unsupported.

    Args:
        path: File path (only the extension is used).

    Returns:
        Language name string (e.g. "python") or None.
    """
    return _EXTENSION_TO_LANGUAGE.get(path.suffix.lower())


def _load_gitignore(root: Path) -> pathspec.PathSpec:
    """Load and compile .gitignore patterns from the repository root.

    Only the root-level .gitignore is loaded. Nested .gitignore files
    are not supported in v1.

    Args:
        root: Repository root directory.

    Returns:
        Compiled PathSpec (empty if no .gitignore present).
    """
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return pathspec.PathSpec.from_lines("gitignore", [])
    lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _compile_exclude_patterns(patterns: list[str]) -> pathspec.PathSpec:
    """Compile configured exclude glob patterns into a PathSpec.

    Args:
        patterns: List of gitignore-style glob strings.

    Returns:
        Compiled PathSpec.
    """
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def discover_files(
    root: Path,
    exclude_patterns: list[str] | None = None,
) -> list[tuple[Path, str]]:
    """Walk the repository tree and return (absolute_path, language) pairs.

    Files matching .gitignore or configured exclude patterns are excluded.
    Files with unsupported extensions are silently skipped.
    The .git directory is always excluded regardless of exclude_patterns.

    Args:
        root: Repository root directory (absolute).
        exclude_patterns: Additional gitignore-style patterns to exclude.
            Defaults to empty list.

    Returns:
        List of (absolute_path, language_name) tuples, in filesystem order.
    """
    if exclude_patterns is None:
        exclude_patterns = []

    gitignore_spec = _load_gitignore(root)
    exclude_spec = _compile_exclude_patterns(exclude_patterns)

    results: list[tuple[Path, str]] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        # Always exclude .git internals
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue

        # Normalize to forward slashes for pathspec matching
        rel_posix = rel.as_posix()

        # Skip .git directory contents
        parts = rel.parts
        if parts and parts[0] == ".git":
            continue

        # Apply .gitignore filtering
        if gitignore_spec.match_file(rel_posix):
            continue

        # Apply configured exclude patterns
        if exclude_spec.match_file(rel_posix):
            continue

        language = detect_language(path)
        if language is None:
            continue

        results.append((path, language))

    return results
