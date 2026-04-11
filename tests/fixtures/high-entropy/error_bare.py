"""Error handling style 1: bare except clause."""


def process_bare(data):
    """Process with bare except — catches all exceptions silently."""
    try:
        result = int(data)
        return result
    except:
        return None
