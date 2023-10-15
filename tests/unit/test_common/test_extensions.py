import unittest
import uuid

from pydantic import BaseModel, ValidationError

from nskit.common.contextmanagers import TestExtension
from nskit.common.extensions import (
    ExtensionsEnum,
    get_extension_names,
    get_extensions,
    load_extension,
)


class ExtensionHelpersTestCase(unittest.TestCase):

    def test_get_extension_name(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension_name, test_entry_point, test):
            self.assertEqual(get_extension_names(test_entry_point), [extension_name])

    def test_load_extension_found(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension_name, test_entry_point, test):
            ep = load_extension(test_entry_point, extension_name)
            self.assertEqual(ep(1), 5)
            self.assertEqual(ep, test)

    def test_load_extension_not_found(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension_name, test_entry_point, test):
            ep = load_extension(test_entry_point, f'test_ext{uuid.uuid4()}')
            self.assertIsNone(ep)

    def test_get_extensions(self):
        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extensions(test_entry_point), {})
        with TestExtension(extension_name, test_entry_point, test):
            eps = get_extensions(test_entry_point)
            self.assertEqual(list(eps.keys()), [extension_name])
            self.assertEqual(eps[extension_name].load()(1), 5)
            self.assertEqual(eps[extension_name].load(), test)


class ExtensionsEnumTestCase(unittest.TestCase):

    def test_enum(self):
        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension_name = f'test_ext{uuid.uuid4()}'

        def test(a):
            return 4+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension_name, test_entry_point, test):
            TestExtensionsEnum = ExtensionsEnum.from_entrypoint('TestExtensionsEnum', test_entry_point)
            self.assertEqual(len(TestExtensionsEnum), 1)
            self.assertEqual(getattr(TestExtensionsEnum, extension_name).value, extension_name)
            self.assertEqual(getattr(TestExtensionsEnum, extension_name).extension, test)
            self.assertEqual(getattr(TestExtensionsEnum, extension_name).extension(1), 5)

    def test_patch(self):

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension1_name = f'test_ext{uuid.uuid4()}'

        def test1(a):
            return 4+a

        extension2_name = f'test_ext{uuid.uuid4()}'

        def test2(a):
            return 5+a

        self.assertEqual(get_extension_names(test_entry_point), [])
        with TestExtension(extension1_name, test_entry_point, test1):
            TestExtensionsEnum = ExtensionsEnum.from_entrypoint('TestExtensionsEnum', test_entry_point)
            self.assertEqual(len(TestExtensionsEnum), 1)
            self.assertEqual(getattr(TestExtensionsEnum, extension1_name).value, extension1_name)
            self.assertEqual(getattr(TestExtensionsEnum, extension1_name).extension, test1)
            self.assertEqual(getattr(TestExtensionsEnum, extension1_name).extension(1), 5)
            with TestExtension(extension2_name, test_entry_point, test2):
                TestExtensionsEnum._patch()
                self.assertEqual(len(TestExtensionsEnum), 2)
                self.assertEqual(getattr(TestExtensionsEnum, extension1_name).value, extension1_name)
                self.assertEqual(getattr(TestExtensionsEnum, extension1_name).extension, test1)
                self.assertEqual(getattr(TestExtensionsEnum, extension1_name).extension(1), 5)
                self.assertEqual(getattr(TestExtensionsEnum, extension2_name).value, extension2_name)
                self.assertEqual(getattr(TestExtensionsEnum, extension2_name).extension, test2)
                self.assertEqual(getattr(TestExtensionsEnum, extension2_name).extension(1), 6)

    def test_patch_basemodel(self):
        # Testing that patch can be used for BaseModel test patching

        test_entry_point = f'nskit.tests.test_extension.a_{uuid.uuid4()}'
        extension1_name = f'test_ext{uuid.uuid4()}'

        def test1(a):
            return 4+a

        extension2_name = f'test_ext{uuid.uuid4()}'

        def test2(a):
            return 5+a

        self.assertEqual(get_extension_names(test_entry_point), [])

        TestExtensionsEnum = ExtensionsEnum.from_entrypoint('TestExtensionsEnum', test_entry_point)

        class TestModel(BaseModel):
            ext: TestExtensionsEnum


        self.assertEqual(len(TestExtensionsEnum), 0)
        with self.assertRaises(ValidationError):
            TestModel(ext=TestExtensionsEnum)
        with TestExtension(extension1_name, test_entry_point, test1):
            TestExtensionsEnum._patch()
            self.assertEqual(len(TestExtensionsEnum), 1)
            self.assertEqual(getattr(TestExtensionsEnum, extension1_name).value, extension1_name)
            model = TestModel(ext= getattr(TestExtensionsEnum, extension1_name))
            self.assertEqual(model.ext, getattr(TestExtensionsEnum, extension1_name))
            with TestExtension(extension2_name, test_entry_point, test2):
                TestExtensionsEnum._patch()
                self.assertEqual(len(TestExtensionsEnum), 2)
                self.assertEqual(getattr(TestExtensionsEnum, extension1_name).value, extension1_name)
                self.assertEqual(getattr(TestExtensionsEnum, extension2_name).value, extension2_name)
                model = TestModel(ext= getattr(TestExtensionsEnum, extension2_name))
                self.assertEqual(model.ext, getattr(TestExtensionsEnum, extension2_name))