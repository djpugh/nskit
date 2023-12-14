"""Common extension helpers."""
from enum import Enum
import sys

if sys.version_info.major >= 3 and sys.version_info.minor >= 10:
    from importlib.metadata import entry_points
else:
    from backports.entry_points_selectable import entry_points

from aenum import extend_enum

from nskit._logging import logger_factory


def get_extension_names(entrypoint: str):
    """Get all installed extension names for a given entrypoint."""
    extensions = []
    for ep in entry_points().select(group=entrypoint):
        extensions.append(ep.name)
    logger_factory.get_logger(__name__).debug(f'Identified extensions {extensions} for entrypoint {entrypoint}')
    return extensions


def load_extension(entrypoint: str, extension: str):
    """Load a given extension for a given entrypoint."""
    for ep in entry_points().select(group=entrypoint, name=extension):
        return ep.load()
    logger_factory.get_logger(__name__).warn(f'Entrypoint {extension} not found for {entrypoint}')


def get_extensions(entrypoint: str):
    """Load all extensions for a given entrypoint."""
    extensions = {}
    for ep in entry_points().select(group=entrypoint):
        extensions[ep.name] = ep
    logger_factory.get_logger(__name__).debug(f'Identified extensions {extensions} for entrypoint {entrypoint}')
    return extensions


class ExtensionsEnum(Enum):
    """Enum created from available extensions on an entrypoint."""

    @classmethod
    def from_entrypoint(cls, name: str, entrypoint: str):
        """Create the enum with name, from entrypoint options."""
        options = {u: u for u in get_extension_names(entrypoint)}
        kls = cls(name, options)
        kls.__entrypoint__ = entrypoint
        return kls

    @property
    def extension(self):
        """Load the extension."""
        return load_extension(self.__entrypoint__, self.value)

    @classmethod
    def _patch(cls):
        """Used for testing and patching objects."""
        options = {u: u for u in get_extension_names(cls.__entrypoint__)}
        # Loop over options not in members
        for key in options:
            if key not in cls._member_names_:
                extend_enum(cls, key, key)
