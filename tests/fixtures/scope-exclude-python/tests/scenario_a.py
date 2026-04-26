"""Test scenario A: bare except with pass (Shape 3).

Structurally distinct from Shapes 1 and 2: no exception type, pass body.
"""


def test_bare_except():
    try:
        risky_op()
    except:  # noqa: E722
        pass


def test_bare_except_silently():
    try:
        another_risky_op()
    except:  # noqa: E722
        pass
