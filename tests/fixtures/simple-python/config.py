"""Configuration for the simple-python fixture."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///simple.db")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
MAX_USERS = 1000


def get_config() -> dict:
    """Return current configuration as a dict."""
    return {
        "database_url": DATABASE_URL,
        "debug": DEBUG,
        "max_users": MAX_USERS,
    }
