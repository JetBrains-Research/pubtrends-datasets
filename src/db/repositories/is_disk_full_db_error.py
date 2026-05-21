import logging

from sqlalchemy.exc import OperationalError as SAOperationalError

from src.exception.disk_space_error import DiskSpaceError

logger = logging.getLogger(__name__)

_DISK_FULL_SQLITE_MESSAGES = (
    "database or disk is full",
    "unable to open database file",
    "disk i/o error",
)


def is_disk_full_sqlite_error(exc: SAOperationalError) -> bool:
    """
    Detect SQLite disk-full errors.

    :param exc: SQLAlchemy OperationalError to inspect.
    :return: True if the error is caused by insufficient disk space.
    """
    orig = exc.orig
    msg = str(orig).lower()                                  # SQLite message-based
    return any(phrase in msg for phrase in _DISK_FULL_SQLITE_MESSAGES)


def handle_disk_space_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SAOperationalError as exc:
            if is_disk_full_sqlite_error(exc):
                logger.critical("Disk space exhausted while writing to database")
                raise DiskSpaceError("No disk space left on device while writing to database") from exc
            raise
    return wrapper
