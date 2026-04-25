"""Parsing module: file discovery and tree-sitter feature extraction.

Public API:
    parse_repository(root, config) -> list[FeatureRecord]
"""

from sdi.parsing._runner import parse_repository
from sdi.parsing.base import LanguageAdapter
from sdi.parsing.discovery import detect_language, discover_files
from sdi.snapshot.model import FeatureRecord

__all__ = [
    "FeatureRecord",
    "LanguageAdapter",
    "detect_language",
    "discover_files",
    "parse_repository",
]
