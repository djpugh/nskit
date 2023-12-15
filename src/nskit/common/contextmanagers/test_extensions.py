"""Context manager for running a test with an extension."""
from __future__ import annotations

from contextlib import ContextDecorator
from importlib.metadata import Distribution, MetadataPathFinder
from pathlib import Path
import sys
from typing import Any

if sys.version_info.major <= 3 and sys.version_info.minor < 11:
    from importlib_metadata import EntryPoint
else:
    from importlib.metadata import EntryPoint

from nskit._logging import logger_factory


class _TestEntrypoint(EntryPoint):

    def __init__(self, name: str, group: str, entrypoint: type, *, solo: bool = False):
        super().__init__(name, f'{entrypoint.__module__}:{entrypoint.__name__}', group)
        self._entrypoint = entrypoint
        self._sys_meta_path = None
        self._solo = solo

    def __setattr__(self, __name: str, __value: Any) -> None:
        return object.__setattr__(self, __name, __value)

    def load(self):
        return self._entrypoint

    def start(self):
        self._sys_meta_path = sys.meta_path[:]
        nested = [u for u in sys.meta_path if isinstance(u, _TestExtensionFinder)]
        if self._solo:
            sys.meta_path = [_TestExtensionFinder(self)]
        elif nested:
            nested[0]._entrypoints.append(self)
        else:
            sys.meta_path.append(_TestExtensionFinder(self))

    def stop(self):
        sys.meta_path = self._sys_meta_path[:]


class _DummyDistribution(Distribution):

    def __init__(self, i: int, entrypoint: EntryPoint):
        self._entrypoint = entrypoint
        self._i = i

    @property
    def metadata(self):
        return {
            'Name': f'DummyDistribution{self._i}'
        }

    @property
    def entry_points(self):
        return [self._entrypoint]

    def read_text(self, filename: str) -> str | None:  # noqa: U100
        return None

    def locate_file(self, path: Path) -> None:  # noqa: U100
        return None


class _TestExtensionFinder(MetadataPathFinder):

    def __init__(self, entrypoint: EntryPoint):
        self._entrypoints = [entrypoint]

    @property
    def extension_distributions(self):
        return [_DummyDistribution(i, u) for i, u in enumerate(self._entrypoints)]

    def find_distributions(self, *args, **kwargs):  # noqa: U100
        # Return the dummy Distribution
        return self.extension_distributions


class TestExtension(ContextDecorator):
    """Context manager for running a test of an entrypoint."""

    def __init__(self, name: str, group: str, entrypoint: type, *, solo: bool = False):
        """Initialise the context manager.

        Keyword Args:
            name (str): the extension name
            group (str): the extension group
            entrypoint (type): the object/type to load in the entrypoint
            solo (bool): set so only that entrypoint will be found (can cause side-effects)
        """
        self.ep = _TestEntrypoint(name=name, group=group, entrypoint=entrypoint, solo=solo)
        self._clean = False

    def __enter__(self):
        """Add the extension so it can be loaded."""
        logger_factory.get_logger(__name__).info(f'Starting entrypoint for extension {self.ep.name} in {self.ep.group}')
        self.ep.start()

    def __exit__(self, *args, **kwargs):  # noqa: U100
        """Remove the extension and return to the original."""
        logger_factory.get_logger(__name__).info(f'Stoppings entrypoint for extension {self.ep.name} in {self.ep.group}')
        self.ep.stop()
