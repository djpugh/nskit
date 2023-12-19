from pathlib import Path
import unittest

from nskit.common.contextmanagers import ChDir
from nskit.mixer import Recipe
from nskit.recipes.python.api import APIRecipe

# Test Recipe created (and validated)



class APIRecipeTestCase(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_dryrun(self):
        with ChDir():
            recipe = APIRecipe(
                name='test_api',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.dryrun()
            wd = Path.cwd()/'test_api'
            expected = self._create_expected(wd, 'test_api')
            self._recursive_dict_compare(expected, results, exists=False)

    def test_create(self):
        with ChDir():
            recipe = APIRecipe(
                name='test_api',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.create()
            wd = Path.cwd()/'test_api'
            expected = self._create_expected(wd, 'test_api')
            self._recursive_dict_compare(expected, results, exists=True)
            missing, errors, ok = recipe.validate()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertNotEqual(ok, [])


    def test_namespace_dryrun(self):
        with ChDir():
            recipe = APIRecipe(
                name='test_api-api2',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.dryrun()
            wd = Path.cwd()/'test_api-api2'
            expected = self._create_expected(wd, 'test_api/api2')
            self._recursive_dict_compare(expected, results, exists=False)

    def test_namespace_create(self):
        with ChDir():
            recipe = APIRecipe(
                name='test_api-api2',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.create()
            wd = Path.cwd()/'test_api-api2'
            expected = self._create_expected(wd, 'test_api/api2')
            self._recursive_dict_compare(expected, results, exists=True)
            missing, errors, ok = recipe.validate()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertNotEqual(ok, [])

    def test_load(self):
        with ChDir():
            recipe = Recipe.load(
                recipe_name='python_api_service',
                name='test_api-api2',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.create()
            wd = Path.cwd()/'test_api-api2'
            expected = self._create_expected(wd, 'test_api/api2')
            self._recursive_dict_compare(expected, results, exists=True)
            missing, errors, ok = recipe.validate()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertNotEqual(ok, [])

    def _recursive_dict_compare(self, one, two, key='<root>', exists=False):
        self.assertEqual(set(one.keys()), set(two.keys()), f'Error in {key}')
        for key, expected_value in one.items():
            if exists:
                self.assertTrue(key.exists())
            if isinstance(expected_value, dict):
                self._recursive_dict_compare(expected_value, two[key], key, exists=exists)
            elif expected_value is not None:
                self.assertEqual(expected_value, two[key], f'Error in {key}')

    @staticmethod
    def _create_expected(root, src_path):
        expected = {
            root:{
                root/'src':{
                    root/'src'/src_path:{
                        root/'src'/src_path/'__init__.py': None,
                        root/'src'/src_path/'app.py': None,
                        root/'src'/src_path/'auth.py': None,
                        root/'src'/src_path/'server.py': None,
                        root/'src'/src_path/'api': {
                            root/'src'/src_path/'api'/'__init__.py': None,
                            root/'src'/src_path/'api'/'base.py': None
                        }
                    }
                },
                root/'tests': {
                    root/'tests'/'unit': {
                        root/'tests'/'unit'/'test_placeholder.py': None
                    },
                    root/'tests'/'functional': {
                        root/'tests'/'functional'/'.git-keep': ""
                    },
                },
                root/'pyproject.toml': None,
                root/'README.md': None,
                root/'.gitignore': None,
                root/'noxfile.py': None,
                root/'.pre-commit-config.yaml': None,
                root/'.dockerignore': None,
                root/'Dockerfile': None,
                root/'docs':{
                    root/'docs'/'mkdocs.yml': None,
                    root/'docs'/'source':{
                        root/'docs'/'source'/'index.md': None,
                        root/'docs'/'source'/'usage.md': None,
                        root/'docs'/'source'/'developing':{
                            root/'docs'/'source'/'developing'/'index.md': None,
                            root/'docs'/'source'/'developing'/'license.md': ''
                        }
                    }
                }
            }
        }
        return expected