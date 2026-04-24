"""Parallel parsing orchestration for parse_repository()."""

from __future__ import annotations

import importlib
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from sdi.config import SDIConfig
from sdi.parsing._parse_cache import compute_file_hash, read_parse_cache, write_parse_cache
from sdi.parsing.discovery import discover_files
from sdi.snapshot.model import FeatureRecord

# Registry of language name → adapter factory
# Each entry is a callable(repo_root) -> LanguageAdapter
_ADAPTER_FACTORIES: dict[str, Any] = {}


def _register_adapters() -> None:
    """Populate _ADAPTER_FACTORIES with available language adapters."""
    global _ADAPTER_FACTORIES
    if _ADAPTER_FACTORIES:
        return

    _adapter_modules = [
        ("python", "sdi.parsing.python", "PythonAdapter"),
        ("typescript", "sdi.parsing.typescript", "TypeScriptAdapter"),
        ("javascript", "sdi.parsing.javascript", "JavaScriptAdapter"),
        ("go", "sdi.parsing.go", "GoAdapter"),
        ("java", "sdi.parsing.java", "JavaAdapter"),
        ("rust", "sdi.parsing.rust", "RustAdapter"),
        ("shell", "sdi.parsing.shell", "ShellAdapter"),
    ]
    for lang, module_path, class_name in _adapter_modules:
        try:
            module = importlib.import_module(module_path)
            _ADAPTER_FACTORIES[lang] = getattr(module, class_name)
        except ImportError as exc:
            print(
                f"[warning] {lang.capitalize()} adapter unavailable: {exc}",
                file=sys.stderr,
            )


def _parse_one(args: tuple[str, str, str, str]) -> FeatureRecord | None:
    """Worker function for ProcessPoolExecutor.

    All arguments and return values must be picklable (no CST objects).

    Checks the parse cache before invoking tree-sitter. On a cache miss,
    parses the file and writes the result to the cache atomically.

    Args:
        args: Tuple of (file_path_str, language, repo_root_str, cache_dir_str).

    Returns:
        FeatureRecord with content_hash populated, or None if parsing failed.
    """
    file_path_str, language, repo_root_str, cache_dir_str = args
    path = Path(file_path_str)
    repo_root = Path(repo_root_str)
    cache_dir = Path(cache_dir_str)

    _register_adapters()
    factory = _ADAPTER_FACTORIES.get(language)
    if factory is None:
        return None

    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        rel = path.relative_to(repo_root)
        print(f"[warning] Skipping {rel}: {exc}", file=sys.stderr)
        return None

    file_hash = compute_file_hash(source_bytes)

    cached = read_parse_cache(cache_dir, file_hash)
    if cached is not None:
        cached.content_hash = file_hash
        return cached

    adapter = factory(repo_root)
    try:
        record = adapter.parse_file(path, source_bytes)
    except Exception as exc:
        rel = path.relative_to(repo_root)
        print(f"[warning] Skipping {rel}: {exc}", file=sys.stderr)
        return None

    if record is not None:
        record.content_hash = file_hash
        try:
            write_parse_cache(cache_dir, file_hash, record)
        except OSError:
            pass

    return record


def parse_repository(root: Path, config: SDIConfig) -> list[FeatureRecord]:
    """Parse all source files in the repository and return FeatureRecords.

    Stage 1 of the SDI pipeline. Parallelized via ProcessPoolExecutor.
    Checks the parse cache (keyed by file content SHA-256) before running
    tree-sitter. Files with unsupported or missing grammars are skipped with
    warnings. If ALL files lack grammars, exits with code 3.

    Args:
        root: Repository root directory (absolute path).
        config: Resolved SDI configuration.

    Returns:
        List of FeatureRecord objects (with content_hash set), one per
        successfully parsed file.

    Raises:
        SystemExit(3): If no files could be parsed (all languages missing grammars).
    """
    _register_adapters()

    discovered = discover_files(root, exclude_patterns=config.core.exclude)
    if not discovered:
        return []

    # Determine which languages have adapters
    available_languages = set(_ADAPTER_FACTORIES.keys())
    files_by_language: dict[str, list[Path]] = {}
    for path, language in discovered:
        files_by_language.setdefault(language, []).append(path)

    supported_languages = set(files_by_language.keys()) & available_languages
    unsupported_languages = set(files_by_language.keys()) - available_languages

    for lang in sorted(unsupported_languages):
        count = len(files_by_language[lang])
        print(
            f"[warning] No grammar for language '{lang}'; "
            f"skipping {count} file(s).",
            file=sys.stderr,
        )

    if not supported_languages:
        print(
            "[error] No supported languages found — all detected languages lack grammars.",
            file=sys.stderr,
        )
        raise SystemExit(3)

    cache_dir_str = str(root / ".sdi" / "cache")

    # Build work items for supported files only
    work_items = [
        (str(path), language, str(root), cache_dir_str)
        for language, paths in files_by_language.items()
        if language in supported_languages
        for path in paths
    ]

    workers = config.core.workers
    if workers == 0:
        workers = min(os.cpu_count() or 1, len(work_items))
    # SDI_WORKERS=1 forces sequential execution (useful for debugging)
    workers = max(1, workers)

    records: list[FeatureRecord] = []

    if workers == 1 or len(work_items) == 1:
        # Sequential fallback — avoids ProcessPoolExecutor overhead
        for item in work_items:
            result = _parse_one(item)
            if result is not None:
                records.append(result)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_parse_one, item): item for item in work_items}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    records.append(result)

    return records
