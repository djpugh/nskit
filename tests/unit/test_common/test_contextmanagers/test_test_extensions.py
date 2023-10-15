import unittest
import uuid

from nskit.common.contextmanagers import TestExtension
from nskit.common.extensions import get_extension_names, load_extension


class TestExtensionTestCase(unittest.TestCase):

    def test_extension_found(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extension_names(test_entry_point), [])


        with TestExtension(extension_name, test_entry_point, test):
            self.assertEqual(get_extension_names(test_entry_point), [extension_name])
            ep = load_extension(test_entry_point, extension_name)
        self.assertEqual(get_extension_names(test_entry_point), [])

    def test_nesting(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension1_name = f'test_ext{uuid.uuid4()}'

        def test1(a):
            return 4+a

        extension2_name = f'test_ext{uuid.uuid4()}'

        def test2(a):
            return 5+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension1_name, test_entry_point, test1):
            self.assertEqual(get_extension_names(test_entry_point), [extension1_name])
            with TestExtension(extension2_name, test_entry_point, test2):
                self.assertEqual(get_extension_names(test_entry_point), [extension1_name, extension2_name])