"""Library Logging Factory."""
from typing import Any, Dict, Optional, Union

from nskit.common.logging.config import LoggingConfig
from nskit.common.logging.formatter import get_library_log_format_string
from nskit.common.logging.logger import get_logger


def get_library_logger(library: str, version: str, name: str, config: Optional[Union[LoggingConfig, Dict[str, Any]]] = None, **kwargs):
    """Get a (sub)logger for a library component, which includes the library and version."""
    if config is None:
        config = {'extra': {}}
    elif isinstance(config, LoggingConfig):
        config = config.model_dump()
    formatstr = get_library_log_format_string(library, version)
    library = {'name': library, 'version': version}
    config['format_string'] = formatstr
    config['extra'] = config.get('extra', {})
    config['extra'].update(kwargs.pop('extra', {}))
    config = LoggingConfig(**config)
    if config.json_format:
        config.extra['library'] = library
    return get_logger(name, config, **kwargs)


class LibraryLoggerFactory:
    """A factory for creating multiple library loggers."""

    def __init__(self, library: str, version: str, base_config: Optional[Union[LoggingConfig, Dict[str, Any]]] = None):
        """Initialise the logger factory."""
        self.__library = library
        self.__version = version
        self.__base_config = base_config

    def get_logger(self, name, config=None, **kwargs):
        """Get the library logger."""
        if config is None:
            config = self.__base_config
        return get_library_logger(self.library, self.version, name, config, **kwargs)

    def get(self, name, config=None, **kwargs):
        """Alias for the get_logger method."""
        return self.get_logger(name, config, **kwargs)

    def getLogger(self, name, config=None, **kwargs):
        """Alias for the get_logger method to provide parity with the standard logging API."""
        return self.get_logger(name, config, **kwargs)

    @property
    def library(self):
        """Return the library name."""
        return self.__library

    @property
    def version(self):
        """Return the version name."""
        return self.__version
