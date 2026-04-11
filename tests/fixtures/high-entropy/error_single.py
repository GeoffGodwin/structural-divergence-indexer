"""Error handling style 2: single named exception with 'as' binding."""


def process_single(data):
    """Process with a single named exception clause."""
    try:
        result = int(data)
        return result
    except ValueError as exc:
        print(f"Conversion failed: {exc}")
        return 0
