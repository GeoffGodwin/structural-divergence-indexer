"""Utility helpers for the simple-python fixture."""

import os
import re
import logging

logger = logging.getLogger(__name__)

_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9\s\-']")


def format_name(name: str) -> str:
    """Format a user name for display.

    Args:
        name: Raw name string.

    Returns:
        Cleaned, title-cased name.
    """
    try:
        cleaned = _NAME_PATTERN.sub("", name).strip()
        if not cleaned:
            raise ValueError("Empty name after cleaning")
        return cleaned.title()
    except ValueError as exc:
        logger.warning("format_name failed: %s", exc)
        return name


def read_env_or_default(key: str, default: str) -> str:
    """Read an environment variable with a fallback default.

    Args:
        key: Environment variable name.
        default: Value to use if the key is not set.

    Returns:
        String value.
    """
    return os.environ.get(key, default)


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug.

    Args:
        text: Input string.

    Returns:
        Lowercase slug with hyphens.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)
