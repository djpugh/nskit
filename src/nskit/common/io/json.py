from typing import Any, BinaryIO, Optional, TextIO

import orjson

# orjson is significantly faster than standard JSON library


def loads(s: str, **kwargs):
    return orjson.loads(s, **kwargs)


def dumps(data: Any, /, default: Optional[Any] = None, option: Optional[int] = None, **kwargs):
    return orjson.dumps(data, default=default, option=option, **kwargs)


def load(fp: TextIO, **kwargs):
    return loads(fp.read(), **kwargs)


def dump(data: Any, fb: BinaryIO, /, default: Optional[Any] = None, option: Optional[int] = None, **kwargs):
    fb.write(dumps(data, default=default, option=option, **kwargs))
