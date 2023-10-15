from nskit import __version__


class LoggerFactory:

    def __init__(self):
        self._factory = None

    def get_logger(self,  name, config=None, **kwargs):
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
