import unittest
from unittest.mock import patch

from nskit.mixer.components.hook import Hook


class HookTestCase(unittest.TestCase):

    def setUp(self):
        self._patch = patch.object(Hook, '__abstractmethods__', set())
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()

    def test_call(self):
        with self.assertRaises(NotImplementedError):
            Hook().call(None, None)

    def test__call__no_result(self):
        class TestHook(Hook):
            def call(sef, recipe_path, context):
                return None

        t = TestHook()
        self.assertEqual(t(1, 2), (1, 2))

    def test__call__result(self):
        class TestHook(Hook):
            def call(sef, recipe_path, context):
                return (3, 4)

        t = TestHook()
        self.assertEqual(t(1, 2), (3, 4))


