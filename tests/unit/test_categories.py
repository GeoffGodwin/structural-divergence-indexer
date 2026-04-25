"""Unit tests for the built-in pattern category registry."""

from __future__ import annotations

from sdi.patterns.categories import (
    CATEGORY_NAMES,
    get_all_categories,
    get_category,
    is_registered_category,
)


def test_all_seven_categories_registered():
    """All seven built-in category names are present in the registry."""
    expected = [
        "error_handling",
        "data_access",
        "logging",
        "async_patterns",
        "class_hierarchy",
        "context_managers",
        "comprehensions",
    ]
    for name in expected:
        assert is_registered_category(name), f"Category '{name}' not in registry"


def test_category_names_list_has_seven_entries():
    """CATEGORY_NAMES exports exactly seven names."""
    assert len(CATEGORY_NAMES) == 7


def test_all_category_names_resolve_without_error():
    """Looking up each built-in category name returns a non-None result."""
    for name in CATEGORY_NAMES:
        defn = get_category(name)
        assert defn is not None, f"get_category('{name}') returned None"
        assert defn.name == name


def test_unknown_category_returns_none_not_exception():
    """Looking up an unknown category name returns None, never raises."""
    result = get_category("completely_unknown_category_xyz")
    assert result is None


def test_is_registered_category_false_for_unknown():
    """is_registered_category returns False for unregistered names."""
    assert not is_registered_category("nonexistent_category")


def test_each_category_has_description():
    """Every registered category has a non-empty description string."""
    for name in CATEGORY_NAMES:
        defn = get_category(name)
        assert defn is not None
        assert isinstance(defn.description, str)
        assert len(defn.description) > 0


def test_each_category_has_python_query():
    """Every built-in category has a tree-sitter query string for Python."""
    for name in CATEGORY_NAMES:
        defn = get_category(name)
        assert defn is not None
        assert "python" in defn.ts_queries, f"No Python query for category '{name}'"
        assert len(defn.ts_queries["python"].strip()) > 0


def test_get_all_categories_returns_seven():
    """get_all_categories returns a dict with all seven built-in entries."""
    all_cats = get_all_categories()
    assert len(all_cats) == 7
    for name in CATEGORY_NAMES:
        assert name in all_cats


def test_get_all_categories_is_copy():
    """Mutating the result of get_all_categories does not affect the registry."""
    all_cats = get_all_categories()
    all_cats["injected"] = None  # type: ignore[assignment]
    assert get_category("injected") is None


# ---------------------------------------------------------------------------
# M14 architecture guard: shell extraction is imperative, not query-based
# ---------------------------------------------------------------------------

_SHELL_PATTERN_CATEGORIES: list[str] = [
    "error_handling",
    "logging",
    "data_access",
    "async_patterns",
]


def test_shell_supported_categories_are_registered():
    """The four shell-pattern categories are present in the built-in registry."""
    for name in _SHELL_PATTERN_CATEGORIES:
        assert is_registered_category(name), f"Shell-pattern category '{name}' missing from registry"


def test_shell_categories_have_no_shell_ts_query():
    """Shell extraction uses _shell_patterns.py, not ts_queries.

    No category's ts_queries dict should have a 'shell' key — shell pattern
    detection is done imperatively by extract_pattern_instances() in
    _shell_patterns.py, not by the tree-sitter query runner.
    """
    all_cats = get_all_categories()
    for name, defn in all_cats.items():
        assert "shell" not in defn.ts_queries, (
            f"Category '{name}' has an unexpected 'shell' key in ts_queries; "
            "shell extraction must go through _shell_patterns.py instead"
        )
