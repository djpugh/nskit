import unittest

from pydantic import TypeAdapter

from nskit.mixer.components._jinja import _PkgResourcesTemplateLoader, TemplateNotFound


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
