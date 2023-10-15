import unittest

from pydantic import TypeAdapter, ValidationError

from nskit.mixer.utilities import Resource


class ResourceTestCase(unittest.TestCase):

    def test_valid(self):
        ta = TypeAdapter(Resource)
        res = ta.validate_python('nskit.mixer:__init__.py')
        self.assertIsInstance(res, Resource)
        self.assertEqual(res, 'nskit.mixer:__init__.py')

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
