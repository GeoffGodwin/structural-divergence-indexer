"""Test scenario B: try/except/finally (Shape 4).

Structurally distinct from Shapes 1-3: has a finally_clause in addition to
the except_clause.
"""


def test_with_finally():
    try:
        process()
    except Exception:
        pass
    finally:
        cleanup()


def test_with_finally_and_resource():
    try:
        acquire_resource()
    except Exception:
        pass
    finally:
        release_resource()
