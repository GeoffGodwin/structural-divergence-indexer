"""Data access style 3: in-memory dict-based store (get/set pattern)."""

_STORE = {}


def store_get(key):
    """Retrieve a value from the in-memory store."""
    return _STORE.get(key)


def store_all():
    """Return all stored values."""
    return list(_STORE.values())
