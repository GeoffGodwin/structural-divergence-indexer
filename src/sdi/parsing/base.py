"""Abstract base class for language adapters."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

from sdi.snapshot.model import FeatureRecord


class LanguageAdapter(ABC):
    """Interface for tree-sitter language adapters.

    Each adapter handles one language: loading its grammar, parsing source
    bytes, and extracting a FeatureRecord. CSTs must NOT be retained after
    parse_file returns — discard them immediately after feature extraction.

    Subclasses must implement all abstract properties and methods.
    """

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Canonical language name (e.g. "python", "typescript")."""

    @property
    @abstractmethod
    def file_extensions(self) -> frozenset[str]:
        """Set of file extensions handled by this adapter (e.g. {".py"})."""

    @abstractmethod
    def parse_file(self, path: Path, source_bytes: bytes) -> FeatureRecord:
        """Parse source bytes and extract a FeatureRecord.

        Implementations MUST discard the tree-sitter CST before returning.
        This method is called in worker processes — all arguments and return
        values must be picklable.

        Args:
            path: Absolute path to the source file (for error messages and
                relative path computation).
            source_bytes: Raw file contents in bytes.

        Returns:
            FeatureRecord with all fields populated.

        Raises:
            Any exception — callers catch and emit a warning, then skip the file.
        """

    def parse_file_safe(
        self,
        path: Path,
        source_bytes: bytes,
        repo_root: Path,
    ) -> FeatureRecord | None:
        """Parse with error handling: return None and warn on failure.

        Args:
            path: Absolute path to the source file.
            source_bytes: Raw file contents.
            repo_root: Repository root for relative path computation.

        Returns:
            FeatureRecord on success, None if parsing fails.
        """
        try:
            return self.parse_file(path, source_bytes)
        except Exception as exc:
            rel = path.relative_to(repo_root) if path.is_absolute() else path
            print(
                f"[warning] Skipping {rel}: {exc}",
                file=sys.stderr,
            )
            return None
