"""Private validation helpers for sdi.config.

This module is imported only by config.py. Do not import it from any other module.
"""

from __future__ import annotations

import sys
import warnings

_KNOWN_SECTIONS = frozenset({"core", "snapshots", "boundaries", "patterns", "thresholds", "change_coupling", "output"})


def _validate_scope_exclude(patterns: list) -> None:
    """Validate patterns.scope_exclude: every entry must be a string.

    Gitignore-style patterns do not have invalid syntax — pathspec treats all
    strings as valid gitignore entries. Only non-string entries are rejected.

    Args:
        patterns: Value of config.patterns.scope_exclude from the merged config dict.

    Raises:
        SystemExit(2): On non-string entry.
    """
    for entry in patterns:
        if not isinstance(entry, str):
            print(
                f"[config error] [patterns] scope_exclude: non-string entry {entry!r}",
                file=sys.stderr,
            )
            raise SystemExit(2)


def _warn_unknown_keys(data: dict) -> None:
    """Emit DeprecationWarning for unrecognized top-level config keys.

    Args:
        data: Merged configuration dict before conversion to SDIConfig.
    """
    for key in data:
        if key not in _KNOWN_SECTIONS:
            warnings.warn(
                f"[config] Unknown configuration key '{key}' — it may have been removed or renamed.",
                DeprecationWarning,
                stacklevel=4,
            )
