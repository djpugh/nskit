from pathlib import Path
import sys
import unittest
from unittest.mock import call, create_autospec, MagicMock, patch

from pydantic import ValidationError

from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.vcs import codebase, settings
from nskit.vcs.codebase import Codebase
from nskit.vcs.namespace_validator import NamespaceValidator
from nskit.vcs.providers import ENTRYPOINT, VCSProviderSettings
from nskit.vcs.repo import NamespaceValidationRepo, RepoClient
from nskit.vcs.settings import CodebaseSettings


class CodebaseTestCase(unittest.TestCase):

    def setUp(self):
        self._MockedRepoClientKls = create_autospec(RepoClient)
        self._mocked_repo_client = self._MockedRepoClientKls()

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self2):
                return self._mocked_repo_client

        self._provider_settings_cls = DummyVCSProviderSettings

    def extension(self):
        return TestExtension('dummy', ENTRYPOINT, self._provider_settings_cls)

    def env(self):
        return Env(override={'TEST_ABACUS': 'A'})

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_no_settings_error(self):

        with ChDir():  # Make sure theres no .env file when running tests
            with Env(remove=['GITHUB_TOKEN', 'GITHUB_JWT_TOKEN']):
                with self.assertRaises(ValidationError):
                    Codebase()
                with self.extension():
                    with Env(remove=['TEST_ABACUS']):
                        with self.assertRaises(ValidationError):
                            Codebase()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_no_settings_ok(self):

        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    c = Codebase()
                    self.assertIsInstance(c.settings, CodebaseSettings)
                    self.assertEqual(c.settings.vcs_provider, settings.ProviderEnum.dummy)

    def test_init_settings(self):
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    s = CodebaseSettings(vcs_provider=settings.ProviderEnum.dummy, default_branch='random')
                    c = Codebase(settings=s)
                    self.assertIsInstance(c.settings, CodebaseSettings)
                    self.assertEqual(c.settings, s)
                    self.assertEqual(c.settings.vcs_provider, settings.ProviderEnum.dummy)

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_namespace_validation_repo_from_settings(self):
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    # We want to set the namespace validation repo
                    r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        default_branch='random',
                        namespace_validation_repo=r
                    )
                    c = Codebase(settings=s)
                    self.assertEqual(c.namespace_validation_repo, r)
                    self.assertEqual(c.namespace_validation_repo.name, 'abc')
                    self.assertEqual(c.namespace_validation_repo.local_dir.name, '.namespaces')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_validation_namespace_local_dir(self):
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    # We want to set the namespace validation repo
                    r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        default_branch='random',
                        namespace_validation_repo=r
                    )
                    c = Codebase(settings=s, namespaces_dir='.namespaces2', root_dir=Path.cwd()/'a')
                    self.assertEqual(c.namespace_validation_repo, r)
                    self.assertEqual(c.namespace_validation_repo.name, 'abc')
                    self.assertEqual(c.namespace_validation_repo.local_dir, Path.cwd()/'a'/'.namespaces2')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_namespace_validator_provided(self):
        r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
        # We need to patch load_namespace_validator()
        r._load_namespace_validator = MagicMock()
        r._load_namespace_validator.return_value = 'a'

        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        default_branch='random',
                        namespace_validation_repo=r
                    )
                    c = Codebase(settings=s)
                    self.assertEqual(c.namespace_validator, 'a')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_namespace_validator_none(self):

        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        default_branch='random',
                        namespace_validation_repo = None
                    )
                    c = Codebase(settings=s)
                    self.assertIsInstance(c.namespace_validator, NamespaceValidator)
                    self.assertIsNone(c.namespace_validator.options)

    def test_list_repos_no_namespace_repo(self):
        self._mocked_repo_client.list.return_value = ['a.b', 'a.d', 'a-c', 'd.e']

        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        namespace_validation_repo = None
                    )
                    c = Codebase(settings=s)
                    self.assertEqual(c.list_repos(), ['a.b', 'a.d', 'a-c', 'd.e'])

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_list_repos_with_namespace_repo(self):
        self._mocked_repo_client.list.return_value = ['a.b', 'a.d', 'a-c', 'd.e']
        nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
        r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
        r._validator = nsv
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    s = CodebaseSettings(
                        vcs_provider=settings.ProviderEnum.dummy,
                        namespace_validation_repo = r
                    )
                    c = Codebase(settings=s)
                    self.assertEqual(c.list_repos(), ['a.b', 'a-c', 'd.e'])

    @patch.object(codebase, 'Repo', autospec=True)
    def test_clone(self, rp):
        rp().exists_locally = False
        # We need to patch things
        # We also need the client to return a differing url based on the name
        names = ['a.b', 'a.d', 'a-c', 'd.e']
        self._mocked_repo_client.list.return_value = names
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    cloned = c.clone()
        rp().clone.assert_has_calls([call(), call(), call(), call()])
        rp().install.assert_has_calls([call(codebase=c, deps=False)]*4+
                                      [call(codebase=c, deps=True)]*4)
        for name in names:
            rp_kwargs = dict(
                name=name,
                local_dir=c.root_dir/name,
                namespace_validation_repo=r,
                validation_level=c.settings.validation_level,
                provider_client=self._mocked_repo_client
            )
            rp.assert_any_call(**rp_kwargs)
        self.assertEqual(len(cloned), len(names))

    @patch.object(codebase, 'Repo', autospec=True)
    def test_create_repo_error_local(self, rp):
        rp().exists_locally = True
        rp().exists = False
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    with self.assertRaises(ValueError):
                        c.create_repo(name='xyz')
        rp.assert_called_with(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )

    @patch.object(codebase, 'Repo', autospec=True)
    def test_create_repo_error_remote(self, rp):
        rp().exists_locally = False
        rp().exists = True
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    with self.assertRaises(ValueError):
                        c.create_repo(name='xyz')
        rp.assert_called_with(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )

    @patch.object(codebase, 'Repo', autospec=True)
    @patch.object(codebase, 'Recipe', autospec=True)
    def test_create_repo_ok(self, recipe, rp):
        rp().exists_locally = False
        rp().exists = False
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.create_repo(name='xyz')
        rp.assert_called_with(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )
        rp().create.assert_called_once_with()
        recipe.load.assert_not_called()
        recipe.load('dummyrecipe',
                    name='xyz',
                    abc='def',
                    repo={'a': 'b', 'url': rp().url, 'repo_separator': '-'}).create.assert_not_called()
        rp().commit.assert_not_called()
        rp().push.assert_not_called()
        rp().install.assert_not_called()

    @patch.object(codebase, 'Repo', autospec=True)
    @patch.object(codebase, 'Recipe', autospec=True)
    def test_create_repo_with_recipe(self, recipe, rp):
        rp().exists_locally = False
        rp().exists = False
        rp().name = 'xyz'
        with ChDir():  # Make sure theres no .env file when running tests
            rp().local_dir = Path.cwd()/'xyz'
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.create_repo(name='xyz', with_recipe='dummyrecipe', abc='def', repo={'a': 'b'})
        rp.assert_called_with(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )
        rp(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        ).create.assert_called_once_with()
        recipe.load.assert_called_once_with(
            'dummyrecipe',
            name='xyz',
            abc='def',
            repo={'a': 'b', 'url': rp().url, 'repo_separator': '-'}
        )
        recipe.load('dummyrecipe',
                    name='xyz',
                    abc='def',
                    repo={'a': 'b', 'url': rp().url, 'repo_separator': '-'}).create.assert_called_once_with(
            base_path=c.root_dir,
            override_path='xyz'
        )
        rp().commit.assert_called_once_with('Initial commit', hooks=False)
        rp().push.assert_called_once_with()
        rp().install.assert_called_once_with(codebase=c, deps=True)

    @patch.object(codebase, 'Repo', autospec=True)
    @patch.object(codebase, 'Recipe', autospec=True)
    def test_create_repo_with_recipe_override_url(self, recipe, rp):
        rp().exists_locally = False
        rp().exists = False
        rp().name = 'xyz'
        with ChDir():  # Make sure theres no .env file when running tests
            rp().local_dir = Path.cwd()/'xyz'
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.create_repo(name='xyz', with_recipe='dummyrecipe', abc='def', repo={'a': 'b', 'url': 'c'})
        recipe.load.assert_called_once_with(
            'dummyrecipe',
            name='xyz',
            abc='def',
            repo={'a': 'b', 'url': 'c', 'repo_separator': '-'}
        )

    @patch.object(codebase, 'Repo', autospec=True)
    @patch.object(codebase, 'Recipe', autospec=True)
    def test_create_repo_with_namespace(self, recipe, rp):
        rp().exists_locally = False
        rp().exists = False
        rp().name = 'a.b'
        with ChDir():  # Make sure theres no .env file when running tests
            rp().local_dir = Path.cwd()/'a'/'b'
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.create_repo(name='a.b', with_recipe='dummyrecipe', abc='def', repo={'a': 'b'})
        rp.assert_called_with(
            name='a.b',
            local_dir=c.root_dir/'a'/'b',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )
        rp(
            name='a.b',
            local_dir=c.root_dir/'a'/'b',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        ).create.assert_called_once_with()
        recipe.load.assert_called_once_with(
            'dummyrecipe',
            name='a-b',
            abc='def',
            repo={'a': 'b', 'url': rp().url, 'repo_separator': '-'}
        )
        recipe.load('dummyrecipe',
                    name='a-b',
                    abc='def',
                    repo={'a': 'b', 'url': rp().url, 'repo_separator': '-'}).create.assert_called_once_with(
            base_path=c.root_dir/'a',
            override_path='b'
        )

    @patch.object(codebase, 'Repo', autospec=True)
    def test_delete_repo(self, rp):
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='abc', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=None)
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.delete_repo('xyz')
        rp.assert_called_with(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )
        rp(
            name='xyz',
            local_dir=c.root_dir/'xyz',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        ).delete.assert_called_once_with()

    @patch.object(codebase, 'Repo', autospec=True)
    def test_delete_repo_with_namespace(self, rp):
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    r = NamespaceValidationRepo(name='a.b', provider_client=self._mocked_repo_client, local_dir=Path.cwd()/'.namespaces')
                    r._validator = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
                    settings.ProviderEnum._patch()
                    c = Codebase(namespace_validation_repo=r)
                    c.delete_repo('a.b')
        rp.assert_called_with(
            name='a.b',
            local_dir=c.root_dir/'a'/'b',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        )
        rp(
            name='a.b',
            local_dir=c.root_dir/'a'/'b',
            namespace_validation_repo=r,
            validation_level=c.settings.validation_level,
            provider_client=self._mocked_repo_client
        ).delete.assert_called_once_with()

    @patch.object(codebase, 'NamespaceValidationRepo', autospec=True)
    def test_create_namespace_repo_name(self, nsv_rp):
        # Check that namespacevalidation repo is initialised and create is called
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    c = Codebase(namespace_validation_repo=None)
        self.assertIsNone(c.namespace_validation_repo)
        options = [{'a': ['b', 'c']}, 'd']
        c.create_namespace_repo(name='test-namespaces', namespace_options=options)
        self.assertIsNotNone(c.namespace_validation_repo)
        nsv_rp.assert_called_once_with(name='test-namespaces', namespaces_filename='namespaces.yaml', local_dir=Path('.namespaces'))
        c.namespace_validation_repo.create.assert_called_once_with(namespace_options=options, delimiters=None, repo_separator=None)

    @patch.object(codebase, 'NamespaceValidationRepo', autospec=True)
    def test_create_namespace_repo_no_name(self, nsv_rp):
        # Check that namespacevalidation repo is initialised and create is called
        with ChDir():  # Make sure theres no .env file when running tests
            with self.extension():
                with self.env():
                    c = Codebase(namespace_validation_repo=None, namespaces_dir=Path('.namespaces2'))

        self.assertIsNone(c.namespace_validation_repo)
        options = [{'a': ['b', 'c']}, 'd']
        c.create_namespace_repo(namespace_options=options)
        self.assertIsNotNone(c.namespace_validation_repo)
        nsv_rp.assert_called_once_with(name='.namespaces2', namespaces_filename='namespaces.yaml', local_dir=Path('.namespaces2'))
        c.namespace_validation_repo.create.assert_called_once_with(namespace_options=options, delimiters=None, repo_separator=None)

