"""Utility functions for multi-language fixture."""


def format_name(name: str) -> str:
    """Return the name with proper casing."""
    return name.strip().title()


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi."""
    try:
        if value < lo:
            return lo
        if value > hi:
            return hi
        return value
    except TypeError as exc:
        raise ValueError(f"Non-numeric value: {exc}") from exc
