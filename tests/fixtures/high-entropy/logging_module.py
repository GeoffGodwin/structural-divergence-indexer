"""Logging style 1: module-level logging via stdlib logging."""

import logging

logger = logging.getLogger(__name__)


def do_work(item):
    """Process item with module-level logger."""
    logger.info("Processing item: %s", item)
    try:
        result = item * 2
        logger.debug("Result computed: %s", result)
        return result
    except TypeError as exc:
        logger.error("Type error on item %s: %s", item, exc)
        return None
