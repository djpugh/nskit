from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import call, create_autospec, MagicMock, NonCallableMagicMock, patch

import git
from pydantic import ValidationError

from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.common.io import yaml
from nskit.vcs import installer, repo, settings
from nskit.vcs.namespace_validator import (
    _DELIMITERS,
    NamespaceValidator,
    REPO_SEPARATOR,
)
from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings
from nskit.vcs.repo import _Repo, NamespaceValidationRepo, Repo, ValidationEnum


class _RepoTestCase(unittest.TestCase):

    def setUp(self):
        self._MockedRepoClientKls = create_autospec(RepoClient)
        self._MockedGitRepoKls = create_autospec(git.Repo)

    def _get_executable_path(self, venv_path):
        if sys.platform.startswith('win'):
            expected = venv_path/'Scripts'/'python.exe'
        else:
            expected = venv_path/'bin'/'python'
        return expected

    def test_init_no_client(self):
        with self.assertRaises(ValidationError):
            with Env(override={'TEST_ABACUS': 'A', 'NSKIT_VCS_CODEBASE_VCS_PROVIDER': 'dummy'}):
                _Repo(name='test')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_with_client(self):
        r = _Repo(name='test', provider_client=RepoClient())
        self.assertEqual(r.local_dir, Path.cwd())
        self.assertEqual(r.default_branch, 'main')
        self.assertEqual(r.name, 'test')

    def test_init_client_from_env(self):

        class DummyVCSProviderSettings(VCSProviderSettings):

            test_abacus: str

            @property
            def repo_client(self2):
                return self._MockedRepoClientKls()


        entrypoint = 'nskit.vcs.providers'
        with ChDir():  # Make sure theres no .env file when running tests
            with TestExtension('dummy', entrypoint, DummyVCSProviderSettings):
                with Env(override={'TEST_ABACUS': 'A', 'NSKIT_VCS_CODEBASE_VCS_PROVIDER': 'dummy'}):
                    settings.ProviderEnum._patch()

                    r = _Repo(name='test')
                    self.assertIsInstance(r.provider_client, NonCallableMagicMock)
                    self.assertIsInstance(r.provider_client, RepoClient)

    def test_url(self):
        cl = self._MockedRepoClientKls()
        cl.get_remote_url.return_value='https://test.com'
        r = _Repo(name='test', provider_client=cl)
        self.assertEqual(r.url, 'https://test.com')
        cl.get_remote_url.assert_called_once_with('test')

    def test_exists(self):
        cl = self._MockedRepoClientKls()
        cl.check_exists.return_value=False
        r = _Repo(name='test', provider_client=cl)
        self.assertFalse(r.exists)
        cl.check_exists.assert_called_once_with('test')
        cl.check_exists.return_value=True
        r = _Repo(name='test-repo', provider_client=cl)
        self.assertTrue(r.exists)
        cl.check_exists.assert_called_with('test-repo')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_exists_locally(self):
        with ChDir():
            r = _Repo(name='test', provider_client=RepoClient())
            self.assertFalse(r.exists_locally)
            Path('.git').mkdir()
            self.assertTrue(r.exists_locally)
            r = _Repo(name='test', provider_client=RepoClient(), local_dir=Path('test'))
            self.assertFalse(r.exists_locally)
            Path('test/.git').mkdir(parents=True)
            self.assertTrue(r.exists_locally)

    def test_create_not_existing_no_url(self):
        with ChDir():
            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = False
            cl.get_clone_url.return_value = None
            r = _Repo(name='test', provider_client=cl)
            r._git_repo_cls = self._MockedGitRepoKls
            r.create()
            cl.check_exists.assert_called_once_with('test')
            cl.create.assert_called_once_with('test')
            r._git_repo_cls.clone_from.assert_not_called()

    def test_create_not_existing_url(self):
        with ChDir():
            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = False
            cl.get_clone_url.return_value = 'https://test.com'
            r = _Repo(name='test', provider_client=cl)
            r._git_repo_cls = self._MockedGitRepoKls
            r.create()
            cl.check_exists.assert_called_once_with('test')
            cl.create.assert_called_once_with('test')
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path.cwd()))

    def test_create_existing_url(self):
        with ChDir():
            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = True
            cl.get_clone_url.return_value = 'https://test.com'
            r = _Repo(name='test', provider_client=cl)
            r._git_repo_cls = self._MockedGitRepoKls
            r.create()
            cl.check_exists.assert_called_once_with('test')
            cl.create.assert_not_called()
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path.cwd()))

    def test_delete_no_local_exists(self):
        with ChDir():
            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = True
            r = _Repo(name='test', provider_client=cl)
            r.delete()
            cl.check_exists.assert_called_once_with('test')
            cl.delete.assert_called_once_with('test')

    def test_delete_no_local_exists_no_remote(self):
        with ChDir():
            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = True
            r = _Repo(name='test', provider_client=cl)
            r.delete(remote=False)
            cl.check_exists.assert_not_called()
            cl.delete.assert_not_called()

    def test_delete_local_no_exists(self):
        with ChDir():
            Path('test/.git').mkdir(parents=True)
            self.assertTrue(Path('test/.git').exists())
            self.assertTrue(Path('test').exists())

            cl = self._MockedRepoClientKls()
            cl.check_exists.return_value = False
            r = _Repo(name='test', provider_client=cl, local_dir=Path('test'))
            r.delete(remote=True)
            self.assertFalse(Path('test/.git').exists())
            self.assertFalse(Path('test').exists())
            cl.check_exists.assert_called_once_with('test')
            cl.delete.assert_not_called()

    def test_clone_exists_local(self):
        with ChDir():
            Path('test/').mkdir(parents=True)
            self.assertTrue(Path('test/').exists())
            cl = self._MockedRepoClientKls()
            cl.get_clone_url.return_value = 'https://test.com'
            r = _Repo(name='test', provider_client=cl, local_dir=Path('test/abc'))
            r._git_repo_cls = self._MockedGitRepoKls
            r.clone()
            self.assertTrue(Path('test/').exists())
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path('test/abc')))

    def test_clone_no_url(self):
        with ChDir():
            self.assertFalse(Path('test/').exists())
            cl = self._MockedRepoClientKls()
            cl.get_clone_url.return_value = None
            r = _Repo(name='test', provider_client=cl, local_dir=Path('test/abc'))
            r._git_repo_cls = self._MockedGitRepoKls
            r.clone()
            self.assertTrue(Path('test/').exists())
            r._git_repo_cls.clone_from.assert_not_called()

    def test_clone_url(self):
        with ChDir():
            self.assertFalse(Path('test/').exists())
            cl = self._MockedRepoClientKls()
            cl.get_clone_url.return_value = 'https://test.com'
            r = _Repo(name='test', provider_client=cl, local_dir=Path('test/abc'))
            r._git_repo_cls = self._MockedGitRepoKls
            r.clone()
            self.assertTrue(Path('test/').exists())
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path('test/abc')))

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_pull(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        r.pull()
        r._git_repo.remotes.origin.pull.assert_called_once_with()
        r._git_repo.remotes.random = create_autospec(git.Remote)
        r.pull(remote='random')
        r._git_repo.remotes.random.pull.assert_called_once_with()

    @patch.object(repo, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_commit_no_paths(self, sp):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        with ChDir():
            Path('test').mkdir()
            r._git_repo.working_tree_dir = Path('test')
            r.commit('x')
            sp.check_call.assert_has_calls([call(['git', 'add', '*']), call(['git', 'commit', '-m', 'x'])])

    @patch.object(repo, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_commit_paths(self, sp):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        with ChDir():
            Path('test').mkdir()
            r._git_repo.working_tree_dir = Path('test')
            r.commit('x', 'a*')
            sp.check_call.assert_has_calls([call(['git', 'add', 'a*']), call(['git', 'commit', '-m', 'x'])])

    @patch.object(repo, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_commit_paths_no_hooks(self, sp):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        with ChDir():
            Path('test').mkdir()
            r._git_repo.working_tree_dir = Path('test')
            r.commit('x', 'a*', hooks=False)
            sp.check_call.assert_has_calls([call(['git', 'add', 'a*']), call(['git', 'commit', '--no-verify', '-m', 'x'])])

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_push(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        r.push()
        r._git_repo.remotes.origin.push.assert_called_once_with()
        r._git_repo.remotes.random = create_autospec(git.Remote)
        r.push(remote='random')
        r._git_repo.remotes.random.push.assert_called_once_with()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_tag(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r.tag('123', 'abc', True)
        r._git_repo.create_tag.assert_called_once_with('123', message='abc', force=True)

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_fetch(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        r.fetch()
        r._git_repo.remotes.origin.fetch.assert_called_once_with()
        r._git_repo.remotes.random = create_autospec(git.Remote)
        r.fetch(remote='random')
        r._git_repo.remotes.random.fetch.assert_called_once_with()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_checkout(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        del r._git_repo.heads.abc
        with self.assertRaises(AttributeError):
            r.checkout('abc', create=False)
        r._git_repo.remotes.origin.fetch.assert_called_once_with()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_checkout_create(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        del r._git_repo.heads.abc
        r.checkout('abc', create=True)
        r._git_repo.remotes.origin.fetch.assert_called_once_with()
        r._git_repo.create_head.assert_called_once_with('abc')
        r._git_repo.create_head('abc').checkout.assert_called_once_with()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_checkout_exists(self):
        r = _Repo(name='test', provider_client=RepoClient())
        r._git_repo_cls = self._MockedGitRepoKls
        r._git_repo.remotes.origin = create_autospec(git.Remote)
        r._git_repo.heads.abc = MagicMock()
        r.checkout('abc', create=True)
        r._git_repo.remotes.origin.fetch.assert_called_once_with()
        r._git_repo.heads.abc.checkout.assert_called_once_with()
        r._git_repo.create_head.assert_not_called()

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_no_content(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.install()
            sp.check_call.assert_not_called()

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_pyproject_toml(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.local_dir.mkdir(exist_ok=True, parents=True)
            with open(r.local_dir/'pyproject.toml', 'w') as f:
                f.write('')
            r.install()
            expected = self._get_executable_path((Path.cwd()/'.venv').absolute())
            sp.check_call.assert_called_once_with([str(expected), '-m', 'pip', 'install', '-e', '.[dev]'])

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_setup_py(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.local_dir.mkdir(exist_ok=True, parents=True)
            with open(r.local_dir/'setup.py', 'w') as f:
                f.write('')
            r.install()
            expected = self._get_executable_path((Path.cwd()/'.venv').absolute())
            sp.check_call.assert_called_once_with([str(expected), '-m', 'pip', 'install', '-e', '.[dev]'])

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_no_deps_requirements(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.local_dir.mkdir(exist_ok=True, parents=True)
            with open(r.local_dir/'requirements.txt', 'w') as f:
                f.write('')
            r.install(deps=False)
            sp.check_call.assert_not_called()

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_deps_requirements(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.local_dir.mkdir(exist_ok=True, parents=True)
            with open(r.local_dir/'requirements.txt', 'w') as f:
                f.write('')
            r.install(deps=True)
            expected = self._get_executable_path((Path.cwd()/'.venv').absolute())
            sp.check_call.assert_called_once_with([str(expected), '-m', 'pip', 'install', '-r', 'requirements.txt'])

    @patch.object(installer, 'subprocess', autospec=True)
    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_install_deps_pyproject_requirements(self, sp):
        with ChDir():
            Path('.venv').mkdir()
            r = _Repo(name='test', provider_client=RepoClient())
            r.local_dir.mkdir(exist_ok=True, parents=True)
            with open(r.local_dir/'pyproject.toml', 'w') as f:
                f.write('')
            with open(r.local_dir/'requirements.txt', 'w') as f:
                f.write('')
            r.install(deps=True)
            expected = self._get_executable_path((Path.cwd()/'.venv').absolute())
            sp.check_call.assert_called_once_with([str(expected), '-m', 'pip', 'install', '-e', '.[dev]'])


class NamespaceValidationRepoTestCase(unittest.TestCase):

    def setUp(self):
        self._MockedRepoClientKls = create_autospec(RepoClient)
        self._MockedGitRepoKls = create_autospec(git.Repo)

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_no_storage(self):
        r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
        self.assertEqual(r.namespaces_filename, 'namespaces.yaml')
        self.assertEqual(r.local_dir, Path(tempfile.tempdir)/'abc')

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_init_storage(self):
        r = NamespaceValidationRepo(
            namespaces_filename='test.yaml',
            name='abc',
            provider_client=RepoClient(),
            local_dir='abc/def')
        self.assertEqual(r.namespaces_filename, 'test.yaml')
        self.assertEqual(r.local_dir, Path('abc/def'))

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_validator(self):
        r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
        # We need to patch load_namespace_validator()
        r._load_namespace_validator = MagicMock()
        r._load_namespace_validator.return_value = 'a'
        self.assertEqual(r.validator, 'a')
        self.assertEqual(r.validator, 'a')
        self.assertEqual(r.validator, 'a')
        r._load_namespace_validator.assert_called_once_with()

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_validate_name(self):
        r = NamespaceValidationRepo(name='abc', provider_client=RepoClient())
        r._validator = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
        self.assertIsInstance(r.validator, NamespaceValidator)
        self.assertEqual(r.validate_name('a.b'), (True, 'ok'))
        self.assertEqual(r.validate_name('a.b.x'), (True, 'ok'))
        self.assertEqual(r.validate_name('a.c'), (True, 'ok'))
        self.assertEqual(r.validate_name('a.c.x'), (True, 'ok'))
        self.assertEqual(r.validate_name('d'), (True, 'ok'))
        self.assertEqual(r.validate_name('d.x'), (True, 'ok'))
        self.assertEqual(r.validate_name('x'), (False, "Does not match valid names for <root>: a, d, with delimiters: ['.', ',', '-']"))
        self.assertEqual(r.validate_name('a.x'), (False, "Does not match valid names for a: b, c, with delimiters: ['.', ',', '-']"))

    def test_download_namespaces(self):
        with ChDir():
            # Only uses clone and checkout, but we can't mock these on the BaseModel
            # Use tests from clone and checkout for _Repo
            cl = self._MockedRepoClientKls()
            cl.get_clone_url.return_value = 'https://test.com'
            r = NamespaceValidationRepo(name='abc', provider_client=cl, local_dir=Path('test/abc'))
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo_cls.clone_from.assert_not_called()
            r._git_repo.remotes.origin = create_autospec(git.Remote)
            # Default branch
            setattr(r._git_repo.heads, r.default_branch, MagicMock())
            r._git_repo_cls.clone_from.assert_not_called()
            r._git_repo.remotes.origin.fetch.assert_not_called()
            r._git_repo.heads.main.checkout.assert_not_called()
            r._download_namespaces()
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path('test/abc')))
            r._git_repo.remotes.origin.fetch.assert_called_once_with()
            r._git_repo.heads.main.checkout.assert_called_once_with()
            r._git_repo.create_head.assert_not_called()

    def test_load_namespace_validator_local_exists(self):
        with ChDir():
            Path('test/abc/.git').mkdir(parents=True, exist_ok=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
            with open('test/abc/namespaces.yaml', 'w') as f:
                f.write(nsv.model_dump_yaml())
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = 'https://test.com'
            r = NamespaceValidationRepo(name='abc', provider_client=cl, local_dir=Path('test/abc'))
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.remotes.origin = create_autospec(git.Remote)
            nsv2 = r._load_namespace_validator()
            r._git_repo.remotes.origin.pull.assert_called_once_with()
            self.assertEqual(nsv, nsv2)

    def test_load_namespace_validator_local_exists_custom_name(self):
        with ChDir():
            Path('test/abc/.git').mkdir(parents=True, exist_ok=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
            with open('test/abc/namespaces2.yaml', 'w') as f:
                f.write(nsv.model_dump_yaml())
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = 'https://test.com'
            r = NamespaceValidationRepo(
                namespaces_filename='namespaces2.yaml',
                name='abc',
                provider_client=cl,
                local_dir=Path('test/abc')
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.remotes.origin = create_autospec(git.Remote)
            nsv2 = r._load_namespace_validator()
            r._git_repo.remotes.origin.pull.assert_called_once_with()
            self.assertEqual(nsv, nsv2)

    def test_load_namespace_validator_local_exists_temp(self):
        with ChDir():
            (Path(tempfile.tempdir)/'abc/.git').mkdir(parents=True, exist_ok=True)
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
            with open(str(Path(tempfile.tempdir)/'abc/namespaces2.yaml'), 'w') as f:
                f.write(nsv.model_dump_yaml())
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = 'https://test.com'
            r = NamespaceValidationRepo(
                namespaces_filename='namespaces2.yaml',
                name='abc',
                provider_client=cl
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.remotes.origin = create_autospec(git.Remote)
            nsv2 = r._load_namespace_validator()
            r._git_repo.remotes.origin.pull.assert_called_once_with()
            self.assertEqual(nsv, nsv2)

    def test_load_namespace_validator_no_local(self):
        with ChDir():
            Path('test/abc/').mkdir(parents=True, exist_ok=True)
            # not creating .git so download_namespaces called as exists_locally is False
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
            with open('test/abc/namespaces2.yaml', 'w') as f:
                f.write(nsv.model_dump_yaml())
            cl = self._MockedRepoClientKls()
            cl.get_clone_url.return_value = 'https://test.com'
            r = NamespaceValidationRepo(
                namespaces_filename='namespaces2.yaml',
                name='abc',
                provider_client=cl,
                local_dir=Path('test/abc')
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.remotes.origin = create_autospec(git.Remote)
            setattr(r._git_repo.heads, r.default_branch, MagicMock())
            nsv2 = r._load_namespace_validator()
            r._git_repo.remotes.origin.pull.assert_called_once_with()
            self.assertEqual(nsv, nsv2)
            r._git_repo_cls.clone_from.assert_called_once_with(url='https://test.com', to_path=str(Path('test/abc')))
            r._git_repo.remotes.origin.fetch.assert_called_once_with()
            r._git_repo.heads.main.checkout.assert_called_once_with()
            r._git_repo.create_head.assert_not_called()


    @patch.object(repo, 'subprocess', autospec=True)
    def test_create_from_validator(self, sp):
        with ChDir():
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'])
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                namespaces_filename='namespaces2.yaml',
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            self.assertFalse(Path('namespaces2.yaml').exists())
            self.assertFalse(Path('README.md').exists())
            r.create(namespace_options=nsv)
            self.assertTrue(Path('namespaces2.yaml').exists())
            self.assertTrue(Path('README.md').exists())
            sp.check_call.assert_has_calls([
                call(['git', 'add', 'namespaces2.yaml', 'README.md']),
                call(['git', 'commit', '-m', 'Initial Namespaces Commit'])
                ])
            with open('namespaces2.yaml') as f:
                nsv2 = NamespaceValidator(**yaml.load(f))
            self.assertEqual(nsv, nsv2)

    @patch.object(repo, 'subprocess', autospec=True)
    def test_create_from_validator_override(self, sp):
        with ChDir():
            nsv = NamespaceValidator(options=[{'a': ['b', 'c']}, 'd'], delimiters=['.'], repo_separator='/')
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            self.assertFalse(Path('namespaces.yaml').exists())
            self.assertFalse(Path('README.md').exists())
            r.create(namespace_options=nsv, delimiters=['.', '-'], repo_separator='-')
            self.assertTrue(Path('namespaces.yaml').exists())
            self.assertTrue(Path('README.md').exists())
            sp.check_call.assert_has_calls([
                call(['git', 'add', 'namespaces.yaml', 'README.md']),
                call(['git', 'commit', '-m', 'Initial Namespaces Commit'])
                ])
            with open('namespaces.yaml') as f:
                nsv2 = NamespaceValidator(**yaml.load(f))
            self.assertNotEqual(nsv2, nsv)
            self.assertEqual(nsv2.options, nsv.options)
            self.assertNotEqual(nsv2.delimiters, nsv.delimiters)
            self.assertNotEqual(nsv2.repo_separator, nsv.repo_separator)
            self.assertEqual(nsv2.delimiters, ['.', '-'])
            self.assertEqual(nsv2.repo_separator, '-')

    @patch.object(repo, 'subprocess', autospec=True)
    def test_create_from_options_override(self, sp):
        with ChDir():
            options=[{'a': ['b', 'c']}, 'd']
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            self.assertFalse(Path('namespaces.yaml').exists())
            self.assertFalse(Path('README.md').exists())
            r.create(namespace_options=options, delimiters=['.'], repo_separator='/')
            self.assertTrue(Path('namespaces.yaml').exists())
            self.assertTrue(Path('README.md').exists())
            sp.check_call.assert_has_calls([
                call(['git', 'add', 'namespaces.yaml', 'README.md']),
                call(['git', 'commit', '-m', 'Initial Namespaces Commit'])
                ])
            with open('namespaces.yaml') as f:
                nsv2 = NamespaceValidator(**yaml.load(f))
            self.assertEqual(nsv2.options, options)
            self.assertEqual(nsv2.delimiters, ['.', '/'])
            self.assertEqual(nsv2.repo_separator, '/')

    @patch.object(repo, 'subprocess', autospec=True)
    def test_create_from_options_default(self, sp):
        with ChDir():
            options=[{'a': ['b', 'c']}, 'd']
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            self.assertFalse(Path('namespaces.yaml').exists())
            self.assertFalse(Path('README.md').exists())
            r.create(namespace_options=options)
            self.assertTrue(Path('namespaces.yaml').exists())
            self.assertTrue(Path('README.md').exists())
            sp.check_call.assert_has_calls([
                call(['git', 'add', 'namespaces.yaml', 'README.md']),
                call(['git', 'commit', '-m', 'Initial Namespaces Commit'])
                ])
            with open('namespaces.yaml') as f:
                nsv2 = NamespaceValidator(**yaml.load(f))
            self.assertEqual(nsv2.options, options)
            self.assertEqual(nsv2.delimiters, _DELIMITERS)
            self.assertEqual(nsv2.repo_separator, REPO_SEPARATOR)


class RepoTestCase(unittest.TestCase):

    def setUp(self):
        self._MockedRepoClientKls = create_autospec(RepoClient)
        self._MockedGitRepoKls = create_autospec(git.Repo)

    def test_validate_name_no_validation(self):
        cl = self._MockedRepoClientKls()
        repo = Repo(name='abc', provider_client=cl)
        self.assertEqual(repo.name, 'abc')
        self.assertEqual(repo.validation_level, ValidationEnum.none)

    def test_validate_name_no_validation_level_set(self):
        cl = self._MockedRepoClientKls()
        repo = Repo(name='abc', provider_client=cl, validation_level=ValidationEnum.strict)
        self.assertEqual(repo.name, 'abc')
        self.assertEqual(repo.validation_level, ValidationEnum.strict)

    @patch.object(repo, 'subprocess', autospec=True)
    def test_validate_name_validation_ok(self, sp):
        with ChDir():
            options=[{'a': ['b', 'c']}, 'd']
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            r.create(namespace_options=options, delimiters=['.', '-'], repo_separator='-')
            repo = Repo(name='a.b.x', provider_client=cl, namespace_validation_repo=r, validation_level=ValidationEnum.strict)
            self.assertEqual(repo.name, 'a-b-x')

    @patch.object(repo, 'subprocess', autospec=True)
    def test_validate_name_validation_warn(self, sp):
        with ChDir():
            options=[{'a': ['b', 'c']}, 'd']
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            r.create(namespace_options=options, delimiters=['.', '-'], repo_separator='-')
            with self.assertWarns(Warning):
                Repo(name='a.g.x', provider_client=cl, namespace_validation_repo=r, validation_level=ValidationEnum.warn)
            with self.assertWarns(Warning):
                Repo(name='abc', provider_client=cl, namespace_validation_repo=r, validation_level=ValidationEnum.warn)
        pass

    @patch.object(repo, 'subprocess', autospec=True)
    def test_validate_name_validation_error(self, sp):
        with ChDir():
            options=[{'a': ['b', 'c']}, 'd']
            cl = self._MockedRepoClientKls()
            cl.get_remote_url.return_value = None
            cl.check_exists.return_value = False
            r = NamespaceValidationRepo(
                name='abc',
                provider_client=cl,
                local_dir=Path.cwd()
            )
            r._git_repo_cls = self._MockedGitRepoKls
            r._git_repo.working_tree_dir = Path.cwd()
            r.create(namespace_options=options, delimiters=['.', '-'], repo_separator='-')
            with self.assertRaises(ValidationError):
                Repo(name='a.g.x', provider_client=cl, namespace_validation_repo=r, validation_level=ValidationEnum.strict)
            with self.assertRaises(ValidationError):
                Repo(name='abc', provider_client=cl, namespace_validation_repo=r, validation_level=ValidationEnum.strict)
