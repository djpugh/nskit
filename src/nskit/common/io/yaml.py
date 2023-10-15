"""Provide a YAML 1.2 Load/Dump API consistent with JSON."""
from typing import Any, Optional, TextIO

from ruamel import yaml

# PyYAML only supports YAML 1.1 (so a: NO -> {"a": False})
# Instead want to use YAML 1.2 (so a: NO -> {"a": "NO"})
# StrictYAML is an alternative, but it is difficult as it casts everything to strings, so needs a schema.


def loads(s: str, *, loader: yaml.Loader = yaml.SafeLoader, **kwargs):
    return yaml.load(s, Loader=loader, **kwargs)


def dumps(data: Any, stream: Optional[Any] = None, *, dumper: yaml.Dumper = yaml.SafeDumper, **kwargs):
    return yaml.dump(data, stream, Dumper=dumper, **kwargs)


def load(fp: TextIO, *, loader: yaml.Loader = yaml.SafeLoader, **kwargs):
    return loads(fp.read(), loader=loader, **kwargs)


def dump(data: Any, fp: TextIO, *, dumper: yaml.Dumper = yaml.SafeDumper, **kwargs):
    fp.write(dumps(data, dumper=dumper, **kwargs))


# TODO: Add !include and !env tag handling
