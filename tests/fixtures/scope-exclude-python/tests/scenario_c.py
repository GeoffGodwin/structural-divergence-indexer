"""Test scenario C: try/except with tuple of exception types (Shape 5).

Structurally distinct from Shapes 1-4: uses a tuple type in the except clause.
"""


def test_multi_except():
    try:
        validate_input()
    except (ValueError, TypeError):
        return None


def test_multi_except_other():
    try:
        parse_value()
    except (ValueError, TypeError):
        return None
