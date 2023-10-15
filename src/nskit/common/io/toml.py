"""Provide a TOML Load/Dump API consistent with JSON."""
from typing import Mapping, TextIO

import tomlkit

# tomllib only provides load/loads


def loads(s: str, **kwargs):
    """Load TOML from string."""
    return tomlkit.loads(s, **kwargs)


def dumps(data: Mapping, sort_keys: bool = False, **kwargs):
    """Dump TOML to string."""
    return tomlkit.dumps(data, sort_keys=sort_keys, **kwargs)


def load(fp: TextIO, **kwargs):
    """Load TOML from file/stream."""
    return tomlkit.load(fp, **kwargs)


def dump(data: Mapping, fp: TextIO, sort_keys: bool = False, **kwargs):
    """Load TOML to file/stream."""
    return tomlkit.dump(data, fp, sort_keys=sort_keys, **kwargs)
