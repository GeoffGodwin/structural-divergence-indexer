"""Post model for the simple-python fixture."""

import logging
from dataclasses import dataclass, field

from . import user as user_module

logger = logging.getLogger(__name__)


@dataclass
class Post:
    """Represents a blog post."""

    title: str
    content: str
    author: "user_module.User | None" = None
    tags: list[str] = field(default_factory=list)

    def publish(self):
        """Mark the post as published."""
        try:
            if not self.title:
                raise ValueError("Post must have a title")
            logger.info("Publishing post: %s", self.title)
            return True
        except ValueError as exc:
            logger.error("Publish failed: %s", exc)
            return False

    def add_tag(self, tag: str):
        """Add a tag to the post."""
        if tag not in self.tags:
            self.tags.append(tag)


MAX_TAGS = 10
