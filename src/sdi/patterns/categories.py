"""Built-in pattern category definitions for SDI.

Defines the seven built-in categories and their tree-sitter query strings for Python.
Other languages register their queries via their adapter modules.

The category registry maps category name to CategoryDefinition. An unknown category
name returns None from get_category() — never an exception.
"""

from __future__ import annotations

from dataclasses import dataclass, field


CATEGORY_NAMES: list[str] = [
    "error_handling",
    "data_access",
    "logging",
    "async_patterns",
    "class_hierarchy",
    "context_managers",
    "comprehensions",
]


@dataclass
class CategoryDefinition:
    """Definition of one built-in pattern category.

    Args:
        name: Canonical category name (e.g., "error_handling").
        description: Human-readable description of what this category captures.
        ts_queries: Tree-sitter query strings keyed by language name.
            A language absent from this dict means no detection for that language.
    """

    name: str
    description: str
    ts_queries: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Python tree-sitter queries for each category
# ---------------------------------------------------------------------------

_PYTHON_QUERIES: dict[str, str] = {
    "error_handling": """
(try_statement) @error_handling
""",
    "data_access": """
(call
  function: (attribute
    attribute: (identifier) @method
    (#match? @method "^(query|execute|filter|filter_by|get|all|first|fetchall|fetchone)$")
  )
) @data_access
""",
    "logging": """
(call
  function: (attribute
    attribute: (identifier) @method
    (#match? @method "^(debug|info|warning|error|critical|exception)$")
  )
) @logging
""",
    "async_patterns": """
(function_definition) @async_def
(await) @await_expr
""",
    "class_hierarchy": """
(class_definition) @class_def
""",
    "context_managers": """
(with_statement) @with_stmt
""",
    "comprehensions": """
(list_comprehension) @list_comp
(dictionary_comprehension) @dict_comp
(set_comprehension) @set_comp
(generator_expression) @gen_expr
""",
}

_DESCRIPTIONS: dict[str, str] = {
    "error_handling": (
        "try/except/raise/finally blocks and error propagation patterns"
    ),
    "data_access": (
        "Function/method calls to data stores, ORM queries, cursor operations"
    ),
    "logging": (
        "Log call sites (logging.*, logger.*, log.*) and their argument shapes"
    ),
    "async_patterns": (
        "async def, await, asyncio.gather, coroutine entry points"
    ),
    "class_hierarchy": (
        "Class definitions with base classes, super() call patterns"
    ),
    "context_managers": (
        "with statement bodies and __enter__/__exit__ pairs"
    ),
    "comprehensions": (
        "List, dict, set, and generator comprehension expressions"
    ),
}


def _build_registry() -> dict[str, CategoryDefinition]:
    """Construct the category registry from built-in definitions."""
    registry: dict[str, CategoryDefinition] = {}
    for name in CATEGORY_NAMES:
        ts_queries: dict[str, str] = {}
        if name in _PYTHON_QUERIES:
            ts_queries["python"] = _PYTHON_QUERIES[name]
        # Shell extraction lives in _shell_patterns.py, not in ts_queries.
        registry[name] = CategoryDefinition(
            name=name,
            description=_DESCRIPTIONS[name],
            ts_queries=ts_queries,
        )
    return registry


_REGISTRY: dict[str, CategoryDefinition] = _build_registry()


def get_category(name: str) -> CategoryDefinition | None:
    """Look up a category definition by name.

    Args:
        name: Category name to look up.

    Returns:
        CategoryDefinition for the name, or None for unknown categories.
        Never raises an exception for unknown names.
    """
    return _REGISTRY.get(name)


def get_all_categories() -> dict[str, CategoryDefinition]:
    """Return a copy of the full category registry.

    Returns:
        Dict mapping category name to CategoryDefinition.
    """
    return dict(_REGISTRY)


def is_registered_category(name: str) -> bool:
    """Return True if the category name is in the built-in registry.

    Args:
        name: Category name to check.

    Returns:
        True if registered, False otherwise.
    """
    return name in _REGISTRY
