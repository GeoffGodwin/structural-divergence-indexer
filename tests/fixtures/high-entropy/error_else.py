"""Error handling style 5: except + else clause."""


def process_else(data):
    """Process with else clause — runs only if no exception raised."""
    try:
        value = int(data)
    except ValueError:
        return None
    else:
        return value * 2
