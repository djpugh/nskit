"""Provide a YAML 1.2 Load/Dump API consistent with JSON."""
from io import StringIO
from typing import Any, TextIO

from ruamel.yaml import YAML as _YAML

# PyYAML only supports YAML 1.1 (so a: NO -> {"a": False})
# Instead want to use YAML 1.2 (so a: NO -> {"a": "NO"})
# StrictYAML is an alternative, but it is difficult as it casts everything to strings, so needs a schema.


def loads(s: str, *, typ: str = 'rt', **kwargs):
    """Load YAML from string."""
    return load(StringIO(s), typ=typ, **kwargs)


def dumps(data: Any, *, typ: str = 'rt', **kwargs):
    """Dump YAML to string."""
    s = StringIO()
    dump(data, s, typ=typ, **kwargs)
    return s.getvalue()


def load(stream: TextIO, *, typ: str = 'rt', **kwargs):
    """Load YAML from file/stream."""
    return _YAML(typ=typ).load(stream, **kwargs)


def dump(data: Any, stream: TextIO, *, typ: str = 'rt', **kwargs):
    """Dump YAML to file/stream."""
    return _YAML(typ=typ).dump(data, stream=stream, **kwargs)

# TODO: Add !include and !env tag handling
