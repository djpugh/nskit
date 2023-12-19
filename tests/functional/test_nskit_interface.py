import os
from pathlib import Path
from typing import List
import unittest
from unittest.mock import call

import nskit

# Patching
from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.recipes.python.package import PackageRecipe
from nskit.vcs import repo, settings
from nskit.vcs.providers import ENTRYPOINT, RepoClient, VCSProviderSettings


class CodeBaseTestCase(unittest.TestCase):

    def setUp(self):

        self._tempdir = ChDir()
        self._tempdir.__enter__()

        calls = {'create': [], 'get_remote_url': [], 'delete': [], 'list': [], 'check_exists': []}

        # We need to have dummy vcs provider handling and patch repo.git for behaviours in the repo

        responses = {'create': None, 'get_remote_url': None, 'delete': None, 'list': None, 'check_exists': None}
        class DummyVCSClient(RepoClient):

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def create(self, repo_name):
                calls['create'].append(call(repo_name))
                return responses['create']

            def get_remote_url(self, repo_name):
                calls['get_remote_url'].append(call(repo_name))
                return responses['get_remote_url']

            def delete(self, repo_name):
                calls['delete'].append(call(repo_name))
                return responses['delete']

            def check_exists(self, repo_name) -> bool:
                calls['check_exists'].append(call(repo_name))
                return responses['check_exists']

            def list(self) -> List[str]:
                calls['list'].append(call())
                return responses['list']

        self._calls = calls
        self._responses = responses


        class DummyVCSProviderSettings(VCSProviderSettings):

            test_parameter_abacus: str

            @property
            def repo_client(self):
                return DummyVCSClient()

        self._provider_settings_cls = DummyVCSProviderSettings
        self._extension = TestExtension('dummy', ENTRYPOINT, self._provider_settings_cls)
        self._extension.__enter__()
        env_vars = self.git_env()
        env_vars.update({'TEST_PARAMETER_ABACUS': 'A'})
        self._env = Env(override=env_vars)
        self._env.__enter__()
        settings.ProviderEnum._patch()
        self._repo_info = {
            'owner': 'Joe Bloggs',
            'email': 'joe.bloggs@test.com',
            'description': 'Test email',
            'url': 'https://www.test.com'
        }

    def git_env(self):
        git_envs = {
            'GIT_AUTHOR_NAME': 'Tester',
            'GIT_AUTHOR_EMAIL': 'test@test.com',
            'GIT_COMMITTER_NAME': 'Tester',
            'GIT_COMMITTER_EMAIL': 'test@test.com'
        }
        return git_envs
        # Configure Git

    def tearDown(self):
        self._extension.__exit__()
        self._env.__exit__
        try:
            self._tempdir.__exit__(None, None, None)
        except (RecursionError, OSError):
            os.chdir(self._tempdir.cwd)

    def test_create_delete_package_repo_namespace(self):
        ns_repo = repo.NamespaceValidationRepo(local_dir=Path.cwd()/'.namespaces')
        ns_repo.create(namespace_options=[{'abc': ['def']}])
        cb = nskit.Codebase(namespace_validation_repo=ns_repo)
        expected_path = Path('abc', 'def', 'ghi')
        self.assertFalse(expected_path. exists())
        created = cb.create_repo(name='abc.def.ghi', with_recipe='python_package', repo=self._repo_info)
        self.assertTrue(expected_path.exists())
        self.assertTrue(Path('.namespaces').exists())
        # Then let's validate that the recipe is correct
        missing, errors, ok = PackageRecipe(
            name = 'abc-def-ghi',
            repo = self._repo_info
        ).validate(override_path='abc/def/ghi')
        self.assertEqual(missing, [])
        self.assertEqual(errors, [])
        self.assertNotEqual(ok, [])
        self.assertIsInstance(ok, list)
        # Test check_exists called in client
        self.assertEqual(self._calls['check_exists'], [call('.namespaces'), call('abc.def.ghi'), call('abc.def.ghi')])
        # Test create called in client
        self.assertEqual(self._calls['create'], [call('.namespaces'), call('abc.def.ghi')])
        # Test expected structure
        expected_structure = self._create_expected(Path('abc/def/ghi').absolute(), 'abc/def/ghi')
        self._recursive_dict_compare(expected_structure, created, exists=True)

        self._responses['check_exists'] = True
        # Test Deleting
        self.assertTrue((expected_path/'src').exists())
        cb.delete_repo('abc.def.ghi')
        self.assertFalse((expected_path/'src').exists())
        # Test check_exists called in client
        self.assertEqual(self._calls['check_exists'], [call('.namespaces'), call('abc.def.ghi'), call('abc.def.ghi'), call('abc.def.ghi')])
        # Test delete called in client
        self.assertEqual(self._calls['delete'], [call('abc.def.ghi')])

    def test_create_delete_package_repo_no_namespace(self):
        cb = nskit.Codebase(namespace_validation_repo=None)
        expected_path = Path('abc.def.ghi')
        self.assertFalse(expected_path. exists())
        created = cb.create_repo(name='abc.def.ghi', with_recipe='python_package', repo=self._repo_info)
        self.assertTrue(expected_path.exists())
        # Then let's validate that the recipe is correct
        missing, errors, ok = PackageRecipe(
            name = 'abc.def.ghi',
            repo = self._repo_info
        ).validate()
        self.assertEqual(missing, [])
        self.assertEqual(errors, [])
        self.assertNotEqual(ok, [])
        self.assertIsInstance(ok, list)
        # Test check_exists called in client
        self.assertEqual(self._calls['check_exists'], [call('abc.def.ghi'), call('abc.def.ghi')])
        # Test create called in client
        self.assertEqual(self._calls['create'], [call('abc.def.ghi')])
        # Test expected structure
        expected_structure = self._create_expected(Path('abc.def.ghi').absolute(), 'abc/def/ghi')
        self._recursive_dict_compare(expected_structure, created, exists=True)

        self._responses['check_exists'] = True
        # Test Deleting
        self.assertTrue((expected_path/'src').exists())
        cb.delete_repo('abc.def.ghi')
        self.assertFalse((expected_path/'src').exists())
        # Test check_exists called in client
        self.assertEqual(self._calls['check_exists'], [call('abc.def.ghi'), call('abc.def.ghi'), call('abc.def.ghi')])
        # Test delete called in client
        self.assertEqual(self._calls['delete'], [call('abc.def.ghi')])

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
                        root/'src'/src_path/'__init__.py': None
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
