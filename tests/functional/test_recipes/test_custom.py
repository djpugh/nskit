from pathlib import Path
from typing import List, Union
import unittest
import uuid

# Test with custom recipe
from pydantic import Field

from nskit.common.contextmanagers import ChDir, TestExtension
from nskit.mixer import File, Folder, Recipe
from nskit.mixer.components.recipe import RECIPE_ENTRYPOINT
from nskit.recipes.python import ingredients, PyRecipe


class CustomRecipeTestCase(unittest.TestCase):

    def setUp(self):

        src_dir = ingredients.src_dir.model_copy(deep=True)
        src_dir['src_path'].contents += [
            File(
                name='app.py',
                content='nskit.recipes.python.ingredients.api:app.py.template'
                )
        ]

        self._test_file = """import {{repo.py_name}}


        print("Hello World")
        """

        self._test_recipe_entrypoint_name = f'test_custom_recipe_{str(uuid.uuid4())}'

        class TestRecipe(PyRecipe):
            script_name: str = 'abacus'
            extension_name: str = self._test_recipe_entrypoint_name

            contents: List[Union[File, Folder]] = Field(
                [
                    ingredients.gitignore,
                    ingredients.noxfile,
                    ingredients.pre_commit,
                    ingredients.test_dir,
                    src_dir,
                    File(name="{{script_name}}.py", content=self._test_file)
                ],
        description='The folder contents')

        self._test_recipe_cls = TestRecipe
        self._test_ext = TestExtension(self._test_recipe_entrypoint_name, RECIPE_ENTRYPOINT, TestRecipe)
        self._test_ext.__enter__()

    def tearDown(self):
        self._test_ext.__exit__()

    def test_dryrun(self):

        with ChDir():
            recipe = Recipe.load(
                recipe_name=self._test_recipe_entrypoint_name,
                name='test_custom',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.dryrun()
            wd = Path.cwd()/'test_custom'
            self.assertEqual(recipe.script_name, 'abacus')
            expected = self._create_expected(wd, recipe.script_name, 'test_custom', 'test_custom')
            self._recursive_dict_compare(expected, results, exists=False)

    def test_create(self):

        with ChDir():
            recipe = Recipe.load(
                recipe_name=self._test_recipe_entrypoint_name,
                name='test_custom-abc',
                script_name='xyz',
                repo={
                    'owner': 'Joe Bloggs',
                    'email': 'joe.bloggs@test.com',
                    'description': 'Test email',
                    'url': 'https://www.test.com'
                }
            )
            results = recipe.create()
            wd = Path.cwd()/'test_custom-abc'
            self.assertEqual(recipe.script_name, 'xyz')
            expected = self._create_expected(wd, recipe.script_name, 'test_custom/abc', 'test_custom.abc')
            self._recursive_dict_compare(expected, results, exists=True)
            missing, errors, ok = recipe.validate()
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertNotEqual(ok, [])

    def _recursive_dict_compare(self, one, two, key='<root>', exists=False):
        self.assertEqual(set(one.keys()), set(two.keys()), f'Error in {key}')
        for key, expected_value in one.items():
            if exists:
                self.assertTrue(key.exists(), f'Error in {key}')
            if isinstance(expected_value, dict):
                self._recursive_dict_compare(expected_value, two[key], key, exists=exists)
            elif expected_value is not None:
                self.assertEqual(expected_value, two[key], f'Error in {key}')

    def _create_expected(self,root, script_name, src_path, repo_py_name):
        expected = {
            root:{
                root/'src':{
                    root/'src'/src_path:{
                        root/'src'/src_path/'__init__.py': None,
                        root/'src'/src_path/'app.py': None,
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
                root/'.gitignore': None,
                root/'noxfile.py': None,
                root/'.pre-commit-config.yaml': None,
                root/f'{script_name}.py': self._test_file.replace('{{repo.py_name}}', repo_py_name),
            }
        }
        return expected