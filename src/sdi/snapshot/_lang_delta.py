"""Per-language delta helpers for snapshot divergence computation.

These functions partition pattern entropy and convention drift by language,
using per-language canonicals for drift so that cross-language shape
similarities don't corrupt language-specific baselines.
"""

from __future__ import annotations

from sdi.patterns.catalog import PatternCatalog
from sdi.patterns.categories import get_category


def build_file_language_map(feature_records: list) -> dict[str, str]:
    """Build a file_path -> language mapping from feature records.

    Args:
        feature_records: List of FeatureRecord objects from a snapshot.

    Returns:
        Dict mapping each file path to its detected language.
    """
    return {rec.file_path: rec.language for rec in feature_records}


def _lang_applies(cat_name: str, lang: str) -> bool:
    """Return True if lang is in scope for cat_name.

    An empty languages set means "applies to all". Unknown categories
    (not in the registry) also apply to all languages.
    """
    defn = get_category(cat_name)
    if defn is None or not defn.languages:
        return True
    return lang in defn.languages


def per_language_pattern_entropy(
    catalog_dict: dict,
    file_lang_map: dict[str, str],
) -> dict[str, float]:
    """Distinct shape count per language across applicable categories.

    Args:
        catalog_dict: Serialized PatternCatalog dict.
        file_lang_map: file_path -> language for the current snapshot.

    Returns:
        Dict mapping language name to distinct shape count (sum across applicable
        categories of shapes that have at least one file of that language).
        Sorted by language name for deterministic output.
    """
    if not catalog_dict or not file_lang_map:
        return {}
    catalog = PatternCatalog.from_dict(catalog_dict)
    languages = set(file_lang_map.values())
    result: dict[str, float] = {}
    for lang in sorted(languages):
        count = 0
        for cat_name, cat in catalog.categories.items():
            if not _lang_applies(cat_name, lang):
                continue
            count += sum(
                1
                for shape in cat.shapes.values()
                if any(file_lang_map.get(fp) == lang for fp in shape.file_paths)
            )
        result[lang] = float(count)
    return result


def per_language_convention_drift(
    catalog_dict: dict,
    file_lang_map: dict[str, str],
) -> dict[str, float]:
    """Non-canonical instance fraction per language using per-language canonicals.

    For each (category, language) pair the canonical is the shape with the most
    instances from files of that language — not the global canonical. This
    prevents a Python canonical from grading shell instances and vice versa.

    Args:
        catalog_dict: Serialized PatternCatalog dict.
        file_lang_map: file_path -> language for the current snapshot.

    Returns:
        Dict mapping language name to non-canonical fraction in [0.0, 1.0].
        Sorted by language name for deterministic output.
    """
    if not catalog_dict or not file_lang_map:
        return {}
    catalog = PatternCatalog.from_dict(catalog_dict)
    languages = set(file_lang_map.values())
    result: dict[str, float] = {}
    for lang in sorted(languages):
        total = 0
        non_canonical = 0
        for cat_name, cat in catalog.categories.items():
            if not _lang_applies(cat_name, lang):
                continue
            lang_counts: dict[str, int] = {}
            for hash_val, shape in cat.shapes.items():
                cnt = sum(1 for fp in shape.file_paths if file_lang_map.get(fp) == lang)
                if cnt > 0:
                    lang_counts[hash_val] = cnt
            if not lang_counts:
                continue
            lang_canonical = max(lang_counts, key=lambda h: lang_counts[h])
            for hash_val, cnt in lang_counts.items():
                total += cnt
                if hash_val != lang_canonical:
                    non_canonical += cnt
        result[lang] = non_canonical / total if total > 0 else 0.0
    return result
