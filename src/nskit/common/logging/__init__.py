"""Common logging helpers."""
from functools import wraps

from .config import LoggingConfig  # noqa: F401
from .library import LibraryLoggerFactory, get_library_logger  # noqa: F401
from .logger import Logger, get_logger  # noqa: F401


@wraps(get_logger)
def getLogger(name, config=None, **kwargs):
    """Get the logger object.

    wraps get_logger.
    """
    return get_logger(name, config, **kwargs)
