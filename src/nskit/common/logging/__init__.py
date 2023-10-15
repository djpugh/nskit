"""Common logging helpers"""
from functools import wraps


from .config import LoggingConfig
from .logger import get_logger, Logger
from .library import get_library_logger, LibraryLoggerFactory

@wraps(get_logger)
def getLogger(name, config=None, **kwargs):
    """Get the logger object."""
    return get_logger(name, config, **kwargs)
