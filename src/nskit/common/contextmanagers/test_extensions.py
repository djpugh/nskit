"""Context manager for running a test with an extension."""
from contextlib import ContextDecorator
from importlib.metadata import Distribution, EntryPoint, MetadataPathFinder
import sys
from typing import Any

from nskit._logging import logger_factory


class _TestEntrypoint(EntryPoint):

    def __init__(self, name: str, group:str, entrypoint: type):
        super().__init__(name, f'{entrypoint.__module__}:{entrypoint.__name__}', group)
        self._entrypoint = entrypoint
        self._sys_meta_path = None

    def __setattr__(self, __name: str, __value: Any) -> None:
        return object.__setattr__(self, __name, __value)

    def load(self):
        return self._entrypoint

    def start(self):
        self._sys_meta_path = sys.meta_path[:]
        sys.meta_path.append(_TestExtensionFinder(self))

    def stop(self):
        sys.meta_path = self._sys_meta_path[:]


class _DummyDistribution(Distribution):

    def __init__(self, entrypoint: EntryPoint):
        self._entrypoint = entrypoint

    @property
    def metadata(self):
        return {
            'Name': 'DummyDistribution'
        }

    @property
    def entry_points(self):
        return [self._entrypoint]


class _TestExtensionFinder(MetadataPathFinder):

    def __init__(self, entrypoint: EntryPoint):
        self._entrypoint = entrypoint

    @property
    def extension_distribution(self):
        return _DummyDistribution(self._entrypoint)

    def find_distributions(self, *args, **kkargs):
        # Return the dummy Distribution
        return [self.extension_distribution]


class TestExtension(ContextDecorator):
    """Context manager for running a test of an entrypoint."""

    def __init__(self, name: str, group:str, entrypoint: type):
        """Initialise the context manager.

        Keyword Args:
            name (str): the extension name
            group (str): the extension group
            entrypoint (type): the object/type to load in the entrypoint
        """
        self.ep = _TestEntrypoint(name=name, group=group, entrypoint=entrypoint)

    def __enter__(self):
        """Add the extension so it can be loaded."""
        logger_factory.get_logger(__name__).info(f'Starting entrypoint for extension {self.name} in {self.group}')
        self.ep.start()

    def __exit__(self, *args):
        """Remove the extension and return to the original."""
        logger_factory.get_logger(__name__).info(f'Stoppings entrypoint for extension {self.name} in {self.group}')
        self.ep.stop()
