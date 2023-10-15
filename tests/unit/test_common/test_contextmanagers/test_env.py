import os
import unittest

from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers.env import Env


class EnvTestCase(unittest.TestCase):

    def test_os_environ_set(self):
        os.environ['NSKIT_TEST_ENV_A'] = '1'
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)
        with Env(environ={'B': '2'}):
            self.assertEqual(os.environ, {'B': '2'})
        self.assertNotEqual(os.environ, {'B': '2'})
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)

    def test_os_environ_override(self):
        os.environ['NSKIT_TEST_ENV_A'] = '1'
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)
        with Env(override={'NSKIT_TEST_ENV_A': '2'}):
            self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '2')
        self.assertNotEqual(os.environ['NSKIT_TEST_ENV_A'], '2',)
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)
        with Env(remove=['NSKIT_TEST_ENV_B']):
            with self.assertRaises(KeyError):
                os.environ['NSKIT_TEST_ENV_B']
                with Env(override={'NSKIT_TEST_ENV_B': '2'}):
                    self.assertEqual(os.environ['NSKIT_TEST_ENV_B'], '2')

    def test_os_environ_remove(self):
        os.environ['NSKIT_TEST_ENV_A'] = '1'
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)
        with Env(remove=['NSKIT_TEST_ENV_A']):
            with self.assertRaises(KeyError):
                os.environ['NSKIT_TEST_ENV_A']
        self.assertNotEqual(os.environ['NSKIT_TEST_ENV_A'], '2',)
        self.assertEqual(os.environ['NSKIT_TEST_ENV_A'], '1',)

    def test_pydantic_config_loading(self):

        class TestConfig(BaseConfiguration):

            nskit_test_field: int = 1

        # REMOVE IF SET
        with Env(remove=['NSKIT_TEST_FIELD']):
            tc = TestConfig()
            self.assertEqual(tc.nskit_test_field, 1)
        # TEST OVERRIDE/SET
        with Env(override={'NSKIT_TEST_FIELD': '3'}):
            tc = TestConfig()
            self.assertEqual(tc.nskit_test_field, 3)
