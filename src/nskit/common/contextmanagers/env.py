"""Context manager for running in a specific directory."""
from contextlib import ContextDecorator
import os
from typing import Dict, List, Optional

from nskit._logging import logger_factory


class Env(ContextDecorator):
    """Context manager for managing environment variables.

    The optional arguments can provide either an exhaustive set of environment values, values to override or values to remove.
    """

    def __init__(
            self,
            environ: Optional[Dict[str, str]] = None,
            override: Optional[Dict[str, str]] = None,
            remove: Optional[List[str]] = None
            ):
        """Initialise the context manager.

        The parameters are applied in the following order (so can be combined): 1st - environ, 2nd - override, 3rd - remove

        Keyword Args:
            environ (Optional[Dict[str, str]]): an exhaustive set of environment values to set (replaces overall os.environ contents)
            override (Optional[Dict[str, str]]): a set of environment values to either override or set (replaces values in existing os.environ)
            remove (Optional[List[str]]): a set of environment values to remove (removes values if found in os.environ )
        """
        if environ is not None and not isinstance(environ, dict):
            raise TypeError('environ should be a dict')
        if override is not None and not isinstance(override, dict):
            raise TypeError('override should be a dict')
        if remove is not None and not isinstance(remove, (list, tuple, set)):
            raise TypeError('remove should be a (list, tuple, set)')
        self._environ = environ
        self._override = override
        self._remove = remove
        self._original = None

    def __enter__(self):
        """Change to the target environment variables."""
        # Handling circular imports with LoggingConfig
        logger = logger_factory.get_logger(__name__)
        if self._environ or self._override or self._remove:
            self._original = os.environ.copy()
            if self._environ is not None:
                # Here we pop all keys from it and then update
                os.environ.clear()
                os.environ.update(self._environ)
            if self._override:
                os.environ.update(self._override)
            if self._remove:
                for key in list(self._remove):
                    os.environ.pop(key, None)
            logger.info('Changing env variables')
            logger.debug(f'New env variables: {os.environ}')
        else:
            logger.info('No arguments set (environ, override, remove)')

    def __exit__(self, *args, **kwargs):  # noqa: U100
        """Reset to the original environment variables."""
        if self._original:
            os.environ.clear()
            os.environ.update(self._original.copy())
