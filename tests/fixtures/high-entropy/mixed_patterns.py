"""Mixed file: combines error handling, data access, and logging patterns."""

import logging

logger = logging.getLogger(__name__)


def load_and_process(session, record_id):
    """Load a record and process it with multiple pattern styles."""
    logger.info("Loading record %s", record_id)
    try:
        record = session.query(Record).filter_by(id=record_id).first()
        if record is None:
            logger.warning("Record %s not found", record_id)
            return None
        return record.value * 2
    except Exception as exc:
        logger.error("Failed to load record %s: %s", record_id, exc)
        return None
