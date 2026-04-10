"""Service layer for the simple-python fixture.

Contains cross-module dependency: imports from models and utils.
"""

import logging

from simple_python.models.user import User, ANONYMOUS
from simple_python.models.post import Post
from simple_python.utils.helpers import format_name, slugify

logger = logging.getLogger(__name__)


class UserService:
    """Handles user management operations."""

    def __init__(self):
        self._users: list[User] = []

    def create_user(self, name: str, email: str) -> User:
        """Create and register a new user."""
        user = User(name=name, email=email)
        try:
            if not user.validate():
                raise ValueError(f"Invalid user data: {name}")
            self._users.append(user)
            logger.info("Created user: %s", format_name(name))
            return user
        except ValueError as exc:
            logger.error("create_user failed: %s", exc)
            raise

    def get_user(self, email: str) -> User:
        """Look up a user by email address."""
        for user in self._users:
            if user.email == email:
                return user
        return ANONYMOUS


class PostService:
    """Handles blog post operations."""

    def __init__(self, user_service: UserService):
        self._user_service = user_service
        self._posts: list[Post] = []

    def create_post(self, title: str, content: str, author_email: str) -> Post:
        """Create a new blog post for a user."""
        author = self._user_service.get_user(author_email)
        post = Post(title=title, content=content, author=author)
        slug = slugify(title)
        try:
            if not post.publish():
                raise RuntimeError(f"Failed to publish: {title}")
            self._posts.append(post)
            logger.info("Published post slug=%s", slug)
            return post
        except RuntimeError as exc:
            logger.error("create_post failed: %s", exc)
            raise
