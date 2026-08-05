"""Compatibility helper for constructing a synchronous ``GhApi``.

ghapi 2.0 made operation calls asynchronous by default, so
``GhApi().licenses.get(...)`` returns a coroutine rather than a response. Code
written against 1.x fails with errors like ``'coroutine' object has no attribute
'body'``. The same release added a ``sync`` constructor flag selecting a
synchronous transport (``SyncOpFunc`` rather than the async ``OpFunc``).

nskit makes a handful of sequential GitHub calls from synchronous code paths --
recipe rendering, repo bootstrapping, backend lookups. Async buys nothing there
and would force ``await`` through every caller and into the ``RepoClient``
interface, so this opts into the synchronous transport instead.

``sync`` does not exist on ghapi 1.x. That version does accept arbitrary keyword
arguments, but they are not necessarily inert, so the flag is passed only when
the installed version actually declares it. That keeps this working across both
majors while ``ghapi`` remains unpinned.
"""

from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def supports_sync_flag() -> bool:
    """Whether the installed ghapi accepts the ``sync`` constructor flag.

    Cached: the answer cannot change within a process, and this is called on
    every client construction.
    """
    from ghapi.all import GhApi

    return "sync" in inspect.signature(GhApi.__init__).parameters


def sync_ghapi(**kwargs: Any):
    """Return a ``GhApi`` whose operations are called synchronously.

    Args:
        **kwargs: Passed through to ``GhApi`` (``token``, ``gh_host``, ...).

    Returns:
        A ``GhApi`` instance that returns responses rather than coroutines.
    """
    from ghapi.all import GhApi

    if supports_sync_flag():
        kwargs.setdefault("sync", True)
    return GhApi(**kwargs)
