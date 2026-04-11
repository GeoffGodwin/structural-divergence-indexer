"""Python service module for multi-language fixture."""

import logging
import os

from .models import User
from .utils import format_name

logger = logging.getLogger(__name__)


class UserService:
    """Manages user operations."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def get_user(self, user_id: int) -> User | None:
        try:
            # Simulate DB lookup
            return User(id=user_id, name="Alice")
        except Exception as exc:
            logger.error("Failed to get user %d: %s", user_id, exc)
            return None

    def create_user(self, name: str) -> User:
        logger.info("Creating user: %s", name)
        formatted = format_name(name)
        return User(id=os.getpid(), name=formatted)
