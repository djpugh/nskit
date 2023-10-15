import os
from pathlib import Path
from typing import List, Union
import unittest

from nskit import __version__
from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers import ChDir, TestExtension
from nskit.common.io import yaml
from nskit.mixer.components.file import File
from nskit.mixer.components.folder import Folder
from nskit.mixer.components.recipe import Recipe


class RecipeTestCase(unittest.TestCase):

    def setUp(self):
        self._recipe = Recipe(
            name='test',
            version='0.1.0',
            contents=[
                Folder(
                    id_='a',
                    name='folder',
                    contents=[
                        File(
                            id_='b',
                            name='test{{x.a}}.txt',
                            content='test')
                        ]
                    ),
                Folder(
                    id_='b',
                    name='folder2',
                    contents=[
                        File(
                            id_='b',
                            name='test2.txt',
                            content='test2{{x.a}}')
                        ]
                )
                ]
            )
        class ExtraModel(BaseConfiguration):
            a: int = 1

            @property
            def random_property(self):
                return 'abacus'

        class TestRecipe(Recipe):
            x: ExtraModel = ExtraModel()
            contents: List[Union[File, 'Folder']] = self._recipe.contents

        self._complex_recipe = TestRecipe(name='test')
        self._complex_recipe_cls = TestRecipe

    def test_recipe(self):
        self.assertEqual(
            self._recipe.recipe,
            {
                'name': 'nskit.mixer.components.recipe:Recipe',
                'version': '0.1.0',
                'extension_name': 'Recipe'
            }
        )

    def test_extension_name_set(self):
        self.assertEqual(self._recipe.extension_name, 'Recipe')
        self._recipe.extension_name = 'test_recipe'
        self.assertEqual(self._recipe.extension_name, 'test_recipe')

    def test_extension_name_from_class(self):
        self.assertEqual(self._recipe.extension_name, 'Recipe')

    def test_create_no_override(self):
        with ChDir():
            path = self._complex_recipe.create(Path.cwd())
            self.assertEqual(path, Path('test').absolute())
            with open('test/folder/test1.txt') as fp:
                self.assertEqual(fp.read(), 'test')
            with open('test/folder2/test2.txt') as fp:
                self.assertEqual(fp.read(), 'test21')
            with open('test/.recipe-batch.yaml') as fp:
                batch = yaml.load(fp)
                self.assertEqual(len(batch), 1)
                self.assertEqual(batch[0]['context'], {'x': {'a': 1, 'random_property': 'abacus'}})
                self.assertEqual(batch[0]['nskit_version'], __version__)
                self.assertEqual(batch[0]['recipe'], {'name': 'test_recipe:TestRecipe', 'version': None, 'extension_name': 'TestRecipe'})


    def test_create_override(self):
        with ChDir():
            path = self._complex_recipe.create(Path.cwd(), Path('abc'))
            self.assertEqual(path, Path('abc').absolute())
            with open('abc/folder/test1.txt') as fp:
                self.assertEqual(fp.read(), 'test')
            with open('abc/folder2/test2.txt') as fp:
                self.assertEqual(fp.read(), 'test21')
            with open('abc/.recipe-batch.yaml') as fp:
                batch = yaml.load(fp)
                self.assertEqual(len(batch), 1)
                self.assertEqual(batch[0]['context'], {'x': {'a': 1, 'random_property': 'abacus'}})
                self.assertEqual(batch[0]['nskit_version'], __version__)
                self.assertEqual(batch[0]['recipe'], {'name': 'test_recipe:TestRecipe', 'version': None, 'extension_name': 'TestRecipe'})

    def test_create_additional_context(self):
        with ChDir():
            path = self._complex_recipe.create(Path.cwd(), x={'a': 3})
            with open('test/folder/test3.txt') as fp:
                self.assertEqual(fp.read(), 'test')
            with open('test/folder2/test2.txt') as fp:
                self.assertEqual(fp.read(), 'test23')
            with open('test/.recipe-batch.yaml') as fp:
                pass
            self.assertEqual(path, Path('test').absolute())

    def test_context(self):
        context = self._recipe.context
        self.assertEqual(context, {})

    def test_context_with_properties(self):

        class TestRecipe(Recipe):

            @property
            def random_property(self):
                return 'abacus'

        t = TestRecipe(name='abc')
        self.assertEqual(t.context, {'random_property': 'abacus'})

    def test_context_with_additional_models(self):
        self.assertEqual(self._complex_recipe.context, {'x': {'a': 1, 'random_property': 'abacus'}})

    def test_dryrun_no_override(self):

        self.assertEqual(
            self._complex_recipe.dryrun(Path('.')),
            {Path('test'): [
                {Path('test/folder'): [
                    {Path('test/folder/test1.txt'): 'test'}
                ]},
                {Path('test/folder2'): [
                    {Path('test/folder2/test2.txt'): 'test21'}
                ]}
            ]}
        )

    def test_dryrun_override(self):
        self.assertEqual(
            self._complex_recipe.dryrun(Path('.'), Path('abc')),
            {Path('abc'): [
                {Path('abc/folder'): [
                    {Path('abc/folder/test1.txt'): 'test'}
                ]},
                {Path('abc/folder2'): [
                    {Path('abc/folder2/test2.txt'): 'test21'}
                ]}
            ]}
        )

    def test_validate_ok(self):
        with ChDir():
            self._complex_recipe.create(Path.cwd())
            missing, errors, ok = self._complex_recipe.validate(Path.cwd())
            self.assertEqual(missing, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(ok), {
                Path('test').absolute(),
                Path('test').absolute()/'folder',
                Path('test').absolute()/'folder'/'test1.txt',
                Path('test').absolute(),
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })

    def test_validate_missing_contents(self):
        with ChDir():
            self._complex_recipe.create(Path.cwd())
            # Delete file
            os.remove(str(Path('test').absolute()/'folder'/'test1.txt'))
            missing, errors, ok = self._complex_recipe.validate(Path.cwd())
            self.assertEqual(missing, [Path('test').absolute()/'folder'/'test1.txt'])
            self.assertEqual(errors, [])
            self.assertEqual(set(ok), {
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'})

    def test_validate_missing(self):
        with ChDir():
            missing, errors, ok = self._complex_recipe.validate(Path.cwd())
            self.assertEqual(ok, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(missing), {
                Path('test').absolute(),
                Path('test').absolute()/'folder',
                Path('test').absolute()/'folder'/'test1.txt',
                Path('test').absolute(),
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })

    def test_validate_missing_override(self):
        with ChDir():
            self._complex_recipe.create(Path.cwd())
            missing, errors, ok = self._complex_recipe.validate(Path.cwd(), Path('abc'))
            self.assertEqual(ok, [])
            self.assertEqual(errors, [])
            self.assertEqual(set(missing), {
                Path('abc').absolute(),
                Path('abc').absolute()/'folder',
                Path('abc').absolute()/'folder'/'test1.txt',
                Path('abc').absolute(),
                Path('abc').absolute()/'folder2',
                Path('abc').absolute()/'folder2'/'test2.txt'
                })


    def test_validate_incorrect_contents_wrong(self):
        with ChDir():
            self._complex_recipe.create(Path.cwd())
            with open(str(Path('test')/'folder'/'test1.txt'), 'w') as f:
                f.write('abacus')
            missing, errors, ok = self._complex_recipe.validate(Path.cwd())
            self.assertEqual(missing, [])
            self.assertEqual(errors, [Path('test').absolute()/'folder'/'test1.txt'])
            self.assertEqual(set(ok), {
                Path('test').absolute()/'folder2',
                Path('test').absolute()/'folder2'/'test2.txt'
                })

    def test_load_recipe_found(self):
        with TestExtension('test_recipe', 'nskit.recipes', self._complex_recipe_cls):
            t = Recipe.load('test_recipe', name='abacus', x={'a': 3})
            self.assertEqual(
                t.dryrun(Path('.')),
                {Path('abacus'): [
                    {Path('abacus/folder'): [
                        {Path('abacus/folder/test3.txt'): 'test'}
                    ]},
                    {Path('abacus/folder2'): [
                        {Path('abacus/folder2/test2.txt'): 'test23'}
                    ]}
                ]}
            )

    def test_repr(self):
        out = repr(self._complex_recipe)
        self.assertEqual(out, "test = TestRecipe(name: test):\n|- folder = Folder(id: a, name: folder):\n  |- test1.txt = File(id: b, name <TemplateStr>: test{{x.a}}.txt)\n|- folder2 = Folder(id: b, name: folder2):\n  |- test2.txt = File(id: b, name: test2.txt)\n\nContext: {'x': {'a': 1, 'random_property': 'abacus'}}")
