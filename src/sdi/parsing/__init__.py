"""Parsing module: file discovery and tree-sitter feature extraction.

Public API:
    parse_repository(root, config) -> list[FeatureRecord]
"""

from sdi.parsing.discovery import discover_files, detect_language
from sdi.parsing.base import LanguageAdapter
from sdi.snapshot.model import FeatureRecord
from sdi.parsing._runner import parse_repository

__all__ = [
    "FeatureRecord",
    "LanguageAdapter",
    "detect_language",
    "discover_files",
    "parse_repository",
]
