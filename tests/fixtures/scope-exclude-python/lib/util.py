"""Utility functions with one canonical error-handling pattern (Shape 1).

try/except with a single named exception type and an assignment in the handler.
"""


def fetch_data(source):
    """Fetch data from source, returning empty dict on missing key."""
    try:
        return source.load()
    except KeyError:
        return {}


def load_config(path):
    """Load config file, returning empty dict on missing key."""
    try:
        return path.read_config()
    except KeyError:
        return {}
