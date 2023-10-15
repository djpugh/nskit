"""Provide a JSON Load/Dump API consistent with stdlib JSON."""
from typing import Any, Optional, TextIO

import orjson

# orjson is significantly faster than standard JSON library


def loads(s: str, **kwargs):
    """Load JSON from string."""
    return orjson.loads(s, **kwargs)


def dumps(data: Any, /, default: Optional[Any] = None, option: Optional[int] = None, **kwargs):
    """Dump JSON to string."""
    return orjson.dumps(data, default=default, option=option, **kwargs).decode()


def load(fp: TextIO, **kwargs):
    """Load JSON from file."""
    return loads(fp.read(), **kwargs)


def dump(data: Any, f: TextIO, /, default: Optional[Any] = None, option: Optional[int] = None, **kwargs):
    """Dump JSON to file."""
    f.write(dumps(data, default=default, option=option, **kwargs))
