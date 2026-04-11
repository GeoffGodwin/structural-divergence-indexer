"""Error handling style 3: tuple of exceptions in a single except clause."""


def process_multi(data):
    """Process with a tuple exception clause."""
    try:
        result = int(data)
        return result
    except (ValueError, TypeError):
        return -1
