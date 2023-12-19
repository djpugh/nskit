import unittest
from unittest.mock import call, DEFAULT, MagicMock, patch

from jinja2 import ChoiceLoader, Environment
from pydantic import TypeAdapter, ValidationError

from nskit.common.contextmanagers import Env, TestExtension
from nskit.mixer import __file__ as init_filepath
from nskit.mixer.utilities import (
    _EnvironmentFactory,
    _PkgResourcesTemplateLoader,
    JINJA_ENVIRONMENT_FACTORY,
    Resource,
    TemplateNotFound,
)


class ResourceTestCase(unittest.TestCase):

    def test_valid(self):
        ta = TypeAdapter(Resource)
        res = ta.validate_python('nskit.mixer:__init__.py')
        self.assertIsInstance(res, Resource)
        self.assertEqual(res, 'nskit.mixer:__init__.py')
        res = ta.validate_python('nskit.mixer:a-b.py')
        self.assertIsInstance(res, Resource)
        self.assertEqual(res, 'nskit.mixer:a-b.py')

    def test_invalid(self):
        ta = TypeAdapter(Resource)
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit.mixer')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python(1)

    def test_invalid_file(self):
        ta = TypeAdapter(Resource)
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit.mixer:component/__init__.py')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit.mixer:')

    def test_invalid_package(self):
        ta = TypeAdapter(Resource)
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit .mixer:__init__.py')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit*.mixer:__init__.py')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nsk-it.mixer:__init__.py')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit(.mixer:__init__.py')
        with self.assertRaises(ValidationError) as e:
            ta.validate_python('nskit).mixer:__init__.py')

    def test_load(self):
        ta = TypeAdapter(Resource)
        res = ta.validate_python('nskit.mixer:__init__.py')
        value = res.load()
        self.assertIn('nskit.mixer', value)


class PkgResourcesTemplateLoaderTestCase(unittest.TestCase):

    def test_get_source_valid(self):
        source, a, b = _PkgResourcesTemplateLoader.get_source(None, 'nskit.mixer:__init__.py')
        self.assertIn('nskit.mixer', source)
        self.assertIsNone(a)
        self.assertTrue(b())

    def test_get_source_invalid(self):
        with self.assertRaises(TemplateNotFound) as e:
            _PkgResourcesTemplateLoader.get_source(None, 'nskit.mixer:component/__init__.py')

    def test_get_source_missing_file(self):
        with self.assertRaises(TemplateNotFound) as e:
            _PkgResourcesTemplateLoader.get_source(None, 'nskit:abacus.py')


class EnvironmentTestCase(unittest.TestCase):

    def test_get_source_valid(self):
        content_str = '{% extends "nskit.mixer:__init__.py" %}'
        result = JINJA_ENVIRONMENT_FACTORY.environment.from_string(content_str).render()
        with open(init_filepath) as f:
            content = f.read()
        self.assertEqual(content.splitlines()[:3], result.splitlines()[:3])

    def test_get_source_invalid(self):
        content_str = '{% extends "nskit.mixer:component/__init__.py" %}'
        with self.assertRaises(TemplateNotFound) as e:
            JINJA_ENVIRONMENT_FACTORY.environment.from_string(content_str).render()

    def test_get_source_missing_file(self):
        content_str = '{% extends "nskit:abacus.py" %}'
        with self.assertRaises(TemplateNotFound) as e:
            JINJA_ENVIRONMENT_FACTORY.environment.from_string(content_str).render()


class EnvironmentFactoryTestCase(unittest.TestCase):

    def test_init(self):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)

    def test_add_extensions(self):
        # Create Extensions for this (2?)
        # Use a magic mock to check add_extension called as expected
        def test_extension_1():
            return ['a', 'b', 'c']

        def test_extension_2():
            return ['c', 'd', 'a']

        with TestExtension('test1', 'nskit.mixer.environment.extensions', test_extension_1):
            # We create a factory and check it here
            factory = _EnvironmentFactory()
            environment = MagicMock()
            factory.add_extensions(environment)
            environment.add_extension.assert_has_calls([call('a'), call('b'), call('c')], any_order=True)
            self.assertEqual(environment.add_extension.call_count, 3)
            with TestExtension('test2', 'nskit.mixer.environment.extensions', test_extension_2):
                environment = MagicMock()
                factory.add_extensions(environment)
                environment.add_extension.assert_has_calls([call('a'), call('b'), call('c'), call('d')], any_order=True)
                self.assertEqual(environment.add_extension.call_count, 4)

    def test_add_extensions_default(self):
        # Use a magic mock to check add_extension not called
        factory = _EnvironmentFactory()
        environment = MagicMock()
        factory.add_extensions(environment)
        environment.add_extension.assert_not_called()

    def test_get_environment(self):
        # Create Extensions for this
        environment1 = MagicMock()
        def test_extension1():
            return environment1

        environment2 = MagicMock()
        def test_extension_2():
            return environment2

        with TestExtension('test1', 'nskit.mixer.environment.factory', test_extension1):
            with TestExtension('test2', 'nskit.mixer.environment.factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={'NSKIT_MIXER_ENVIRONMENT_FACTORY': 'test1'}):
                    self.assertEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)

    def test_get_environment_default(self):
        # Create Extensions for this
        environment1 = MagicMock()
        def test_extension1():
            return environment1

        environment2 = MagicMock()
        def test_extension_2():
            return environment2

        with TestExtension('test1', 'nskit.mixer.environment.factory', test_extension1):
            with TestExtension('test2', 'nskit.mixer.environment.factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(override={'NSKIT_MIXER_ENVIRONMENT_FACTORY': 'default'}):
                    self.assertNotEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)
                    self.assertIsInstance(factory.get_environment(), Environment)

    def test_get_environment_none(self):
        # Create Extensions for this
        environment1 = MagicMock()
        def test_extension1():
            return environment1

        environment2 = MagicMock()
        def test_extension_2():
            return environment2

        with TestExtension('test1', 'nskit.mixer.environment.factory', test_extension1):
            with TestExtension('test2', 'nskit.mixer.environment.factory', test_extension_2):
                factory = _EnvironmentFactory()
                with Env(remove=['NSKIT_MIXER_ENVIRONMENT_FACTORY']):
                    self.assertNotEqual(factory.get_environment(), environment1)
                    self.assertNotEqual(factory.get_environment(), environment2)
                    self.assertIsInstance(factory.get_environment(), Environment)

    def test_environment_exists(self):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        factory._environment = 'a'
        self.assertEqual(factory.environment, 'a')

    @patch.multiple(_EnvironmentFactory, get_environment=DEFAULT, add_extensions=DEFAULT)
    def test_environment_not_exists(self, get_environment, add_extensions):
        factory = _EnvironmentFactory()
        self.assertIsNone(factory._environment)
        get_environment.return_value =  'a'
        self.assertEqual(factory.environment, 'a')
        self.assertEqual(factory._environment, 'a')
        get_environment.assert_called_once_with()
        add_extensions.assert_called_once_with('a')

    def test_default_environment(self):
        # Check loader is correct
        environment = _EnvironmentFactory.default_environment()
        self.assertIsInstance(environment, Environment)
        self.assertIsInstance(environment.loader, ChoiceLoader)
        self.assertIsInstance(environment.loader.loaders[0], _PkgResourcesTemplateLoader)