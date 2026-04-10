"""User model for the simple-python fixture."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class User:
    """Represents a user account."""

    name: str
    email: str

    def validate(self):
        """Validate the user data.

        Returns:
            True if valid, False otherwise.
        """
        try:
            if not self.name:
                raise ValueError("Name cannot be empty")
            if "@" not in self.email:
                raise ValueError("Invalid email")
            return True
        except ValueError as exc:
            logger.error("Validation failed: %s", exc)
            return False

    def display(self):
        """Return a human-readable display string."""
        return f"{self.name} <{self.email}>"


ANONYMOUS = User(name="anonymous", email="noreply@example.com")
