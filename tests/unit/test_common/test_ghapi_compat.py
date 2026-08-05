"""Unit tests for the ghapi sync-transport compatibility helper."""

from __future__ import annotations

import inspect
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import nskit
from nskit.common import ghapi_compat
from nskit.common.ghapi_compat import supports_sync_flag, sync_ghapi


class TestSupportsSyncFlag(unittest.TestCase):
    """Detection of the ghapi 2.x ``sync`` constructor flag."""

    def setUp(self) -> None:
        """Clear the cache so each test sees a fresh detection."""
        supports_sync_flag.cache_clear()
        self.addCleanup(supports_sync_flag.cache_clear)

    def test_detects_flag_when_declared(self) -> None:
        """A constructor declaring ``sync`` is detected."""

        class FakeGhApi:
            def __init__(self, token=None, sync=False):  # noqa: ARG002
                pass

        with patch("ghapi.all.GhApi", FakeGhApi):
            self.assertTrue(supports_sync_flag())

    def test_detects_absence_on_1x_signature(self) -> None:
        """A 1.x-style constructor without ``sync`` is detected as unsupported.

        1.x accepts ``**kwargs``, so the flag must not be inferred from the
        call succeeding -- only from the signature declaring it.
        """

        class FakeGhApi:
            def __init__(self, token=None, **kwargs):  # noqa: ARG002
                pass

        with patch("ghapi.all.GhApi", FakeGhApi):
            self.assertFalse(supports_sync_flag())

    def test_result_is_cached(self) -> None:
        """Detection runs once per process."""
        with patch.object(ghapi_compat.inspect, "signature", wraps=inspect.signature) as sig:
            supports_sync_flag()
            supports_sync_flag()
        self.assertEqual(sig.call_count, 1)


class TestSyncGhApi(unittest.TestCase):
    """Construction of a synchronous client."""

    def setUp(self) -> None:
        """Clear the cache so each test controls the detected version."""
        supports_sync_flag.cache_clear()
        self.addCleanup(supports_sync_flag.cache_clear)

    def test_passes_sync_on_2x(self) -> None:
        """``sync=True`` is passed when the constructor declares it."""
        captured = {}

        class FakeGhApi:
            def __init__(self, token=None, sync=False):
                captured["token"] = token
                captured["sync"] = sync

        with patch("ghapi.all.GhApi", FakeGhApi):
            sync_ghapi(token="t")
        self.assertEqual(captured, {"token": "t", "sync": True})

    def test_omits_sync_on_1x(self) -> None:
        """``sync`` is not passed to a version that does not declare it.

        Passing an unknown keyword to 1.x is not guaranteed to be inert, so it
        is withheld rather than relied upon.
        """
        captured = {}

        class FakeGhApi:
            def __init__(self, token=None, **kwargs):
                captured["token"] = token
                captured["kwargs"] = kwargs

        with patch("ghapi.all.GhApi", FakeGhApi):
            sync_ghapi(token="t")
        self.assertEqual(captured, {"token": "t", "kwargs": {}})

    def test_caller_can_override_sync(self) -> None:
        """An explicit ``sync`` from the caller wins."""
        captured = {}

        class FakeGhApi:
            def __init__(self, sync=False):
                captured["sync"] = sync

        with patch("ghapi.all.GhApi", FakeGhApi):
            sync_ghapi(sync=False)
        self.assertFalse(captured["sync"])

    def test_other_kwargs_pass_through(self) -> None:
        """Unrelated keyword arguments reach the constructor untouched."""
        captured = {}

        class FakeGhApi:
            def __init__(self, token=None, gh_host=None, sync=False):
                captured.update(token=token, gh_host=gh_host, sync=sync)

        with patch("ghapi.all.GhApi", FakeGhApi):
            sync_ghapi(token="t", gh_host="https://ghe.example.com")
        self.assertEqual(captured["gh_host"], "https://ghe.example.com")


class TestNoDirectGhApiConstruction(unittest.TestCase):
    """No source file constructs ``GhApi`` directly.

    A direct construction silently returns an async client on ghapi 2.x, and the
    failure surfaces far from the cause (``'coroutine' object has no attribute
    ...``). This guard means a new call site cannot reintroduce that.
    """

    def test_all_construction_goes_through_the_helper(self) -> None:
        """``GhApi(`` appears nowhere in src except the compat helper itself."""
        src = Path(nskit.__file__).parent
        offenders = []
        for path in src.rglob("*.py"):
            if path.name == "ghapi_compat.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if re.search(r"\bGhApi\s*\(", line):
                    offenders.append(f"{path.relative_to(src)}:{number}")
        self.assertFalse(
            offenders,
            f"construct clients via nskit.common.ghapi_compat.sync_ghapi instead of GhApi() directly: {offenders}",
        )


class TestInstalledGhapiIsSynchronous(unittest.TestCase):
    """The helper yields a synchronous client against the installed ghapi.

    Unlike the tests above, this exercises the real library, so it catches the
    actual regression: a client whose operations return coroutines.
    """

    def test_operations_are_not_coroutine_functions(self) -> None:
        """A real client's operations are callable synchronously."""
        api = sync_ghapi()
        self.assertFalse(
            inspect.iscoroutinefunction(api.licenses.get.__call__),
            "ghapi operations are async; the sync transport was not selected",
        )


if __name__ == "__main__":
    unittest.main()
