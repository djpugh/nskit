import unittest

from pydantic import TypeAdapter, ValidationError

from nskit.mixer import __file__ as init_filepath
from nskit.mixer.utilities import (
    _PkgResourcesTemplateLoader,
    JINJA_ENVIRONMENT,
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
        result = JINJA_ENVIRONMENT.from_string(content_str).render()
        with open(init_filepath) as f:
            content = f.read()
        self.assertEqual(content.splitlines()[:3], result.splitlines()[:3])

    def test_get_source_invalid(self):
        content_str = '{% extends "nskit.mixer:component/__init__.py" %}'
        with self.assertRaises(TemplateNotFound) as e:
            JINJA_ENVIRONMENT.from_string(content_str).render()

    def test_get_source_missing_file(self):
        content_str = '{% extends "nskit:abacus.py" %}'
        with self.assertRaises(TemplateNotFound) as e:
            JINJA_ENVIRONMENT.from_string(content_str).render()