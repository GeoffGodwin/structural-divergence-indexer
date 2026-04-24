import logging

logger = logging.getLogger(__name__)


def report(msg: str) -> None:
    logger.info(msg)
    logger.warning("done: %s", msg)
