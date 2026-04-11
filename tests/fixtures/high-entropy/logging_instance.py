"""Logging style 2: instance logger on a class."""

import logging


class Worker:
    """A worker that uses an instance logger."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.Worker")

    def run(self, task):
        """Execute task with instance logger."""
        self.logger.info("Starting task: %s", task)
        self.logger.warning("No-op implementation — override in subclass")
        return None
