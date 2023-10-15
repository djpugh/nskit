from pathlib import Path
from typing import List
import unittest

import nskit
# Patching
from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.recipes.python.package import PackageRecipe
from nskit.vcs import repo, settings
from nskit.vcs.providers import ENTRYPOINT, RepoClient, VCSProviderSettings


class CodeBaseInheritanceTestCase(unittest.TestCase):

    def setUp(self):

        self._tempdir = ChDir()
        self._tempdir.__enter__()

        # TODO: Create the namespace validator and root


        class InheritedCodebase(nskit.Codebase):
            namespace_validation_repo: repo.NamespaceValidationRepo = repo.NamespaceValidationRepo()
            virtualenv_args: List[str] = []

        self._inherited_codebase_cls = InheritedCodebase

        # We need to have dummy vcs provider handling and patch repo.git for behaviours in the repo

        class DummyVCSClient(RepoClient):

            def create(self, repo_name):
                pass

            def get_remote_url(self, repo_name):
                pass

            def delete(self, repo_name):
                pass

            def check_exists(self, repo_name) -> bool:
                pass

            def list(self) -> List[str]:
                pass

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_parameter_abacus: str

            @property
            def repo_client(self):
                return DummyVCSClient()

        self._provider_settings_cls = DummyVCSProviderSettings
        self._extension = TestExtension('dummy', ENTRYPOINT, self._provider_settings_cls)
        self._extension.__enter__()
        self._env = Env(override={'TEST_PARAMETER_ABACUS': 'A'})
        self._env.__enter__()
        settings.ProviderEnum._patch()

    def tearDown(self):
        self._extension.__exit__()
        self._tempdir.__exit__()
        self._env.__exit__()


    def test_create_package_repo(self):
        self._inherited_codebase_cls()
        expected_path = Path('abc', 'def', 'ghi')
        self.assertFalse(expected_path. exists())
        nskit.create_repo(name='abc.def.ghi', with_recipe='python_package')
        self.assertTrue(expected_path.exists())
        # Then let's validate that the recipe is correct
        missing, errors, ok = PackageRecipe(
            ...
        ).validate()
        self.assertEqual(missing, [])
        self.assertEqual(errors, [])
        self.assertNotEqual(ok, [])
        self.assertIsInstance(ok, list)
        # Test check_exists called in client
        # Test create called in client

    def test_delete_repo(self):
        self._inherited_codebase_cls()
        expected_path = Path('abc', 'def', 'ghi')
        self.assertFalse(expected_path. exists())
        nskit.create_repo(name='abc.def.ghi', with_recipe='python_package')
        self.assertTrue(expected_path.exists())
        nskit.delete_repo()
        self.assertFalse(expected_path. exists())
        # Test check_exists called in client
        # Test delete called in client
