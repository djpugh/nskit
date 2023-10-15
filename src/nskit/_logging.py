"""Logging helper.

Creates a logger factory object for use in the nskit library.
"""
from nskit import __version__


class LoggerFactory:
    """Provides same API as LoggerFactory."""

    def __init__(self):
        """Initialise the factory."""
        self._factory = None

    def get_logger(self,  name, config=None, **kwargs):
        """Get the logger for a name."""
        # Has in-class imports to avoid circular imports.
        from nskit.common.logging.library import LibraryLoggerFactory
        if self._factory is None:
            self._factory = LibraryLoggerFactory('nskit', __version__)
        return self._factory.get_logger(name, config=config, **kwargs)

    def get(self, name, config=None, **kwargs):
        """Alias for the get_logger method."""
        return self.get_logger(name, config, **kwargs)

    def getLogger(self, name, config=None, **kwargs):
        """Alias for the get_logger method to provide parity with the standard logging API."""
        return self.get_logger(name, config, **kwargs)


logger_factory = LoggerFactory()
