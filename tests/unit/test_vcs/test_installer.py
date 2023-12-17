from pathlib import Path
import sys
import unittest
from unittest.mock import call, create_autospec, MagicMock, patch

from pydantic import ValidationError

from nskit.common.contextmanagers import ChDir, Env, TestExtension
from nskit.vcs import codebase, settings
from nskit.vcs.codebase import Codebase
import nskit.vcs.installer as installer
from nskit.vcs.installer import ENTRYPOINT, Installer, PythonInstaller
from nskit.vcs.namespace_validator import NamespaceValidator
from nskit.vcs.providers import ENTRYPOINT as PROVIDER_ENTRYPOINT
from nskit.vcs.providers import VCSProviderSettings
from nskit.vcs.repo import NamespaceValidationRepo, RepoClient
from nskit.vcs.settings import CodebaseSettings


class InstallerTestCase(unittest.TestCase):

    @patch.object(Installer, '__abstractmethods__', set())
    def test_check_not_enabled(self):

        installer = Installer(enabled=False)
        self.assertFalse(installer.check(Path.cwd()))

    @patch.object(Installer, '__abstractmethods__', set())
    def test_check_enabled(self):
        with self.assertRaises(NotImplementedError):
            installer = Installer()
            installer.check(Path.cwd())

    @patch.object(Installer, '__abstractmethods__', set())
    def test_install(self):
        with self.assertRaises(NotImplementedError):
            installer = Installer()
            installer.install(None)

class PythonInstallerTestCase(unittest.TestCase):

    def _get_executable_path(self, venv_path):
        if sys.platform.startswith('win'):
            expected = venv_path/'Scripts'/'python.exe'
        else:
            expected = venv_path/'bin'/'python'
        return expected

    def test_init_env_vars(self):
        with Env(override={
                    'NSKIT_PYTHON_INSTALLER_VIRTUALENV_DIR': '.virtualenv',
                    'NSKIT_PYTHON_INSTALLER_VIRTUALENV_ARGS': '["--seeder","azdo-pip"]'
                    }):
            with ChDir():
                installer = PythonInstaller()
                self.assertEqual(installer.virtualenv_dir, Path('.virtualenv'))
                self.assertEqual(installer.virtualenv_args, ['--seeder', 'azdo-pip'])

    def test_check_repo_setup(self):
        with ChDir():
            setup = Path('test')/'setup.py'
            setup.parent.mkdir()
            installer = PythonInstaller()
            self.assertFalse(installer.check_repo(Path.cwd()))
            self.assertFalse(installer.check_repo(Path.cwd()/'test'))
            with setup.open('w') as f:
                f.write('\n')
            self.assertTrue(setup.exists())
            self.assertTrue(installer.check_repo(Path.cwd()/'test'))

    def test_check_repo_pyprojects(self):
        with ChDir():
            pyproject = Path('test')/'pyproject.toml'
            pyproject.parent.mkdir()
            installer = PythonInstaller()
            self.assertFalse(installer.check_repo(Path.cwd()))
            self.assertFalse(installer.check_repo(Path.cwd()/'test'))
            with pyproject.open('w') as f:
                f.write('\n')
            self.assertTrue(pyproject.exists())
            self.assertTrue(installer.check_repo(Path.cwd()/'test'))

    def test_check_repo_requirements(self):
        with ChDir():
            requirements = Path('test')/'requirements.txt'
            requirements.parent.mkdir()
            installer = PythonInstaller()
            self.assertFalse(installer.check_repo(Path.cwd()))
            self.assertFalse(installer.check_repo(Path.cwd()/'test'))
            with requirements.open('w') as f:
                f.write('\n')
            self.assertTrue(requirements.exists())
            self.assertTrue(installer.check_repo(Path.cwd()/'test'))

    def test_check_not_python(self):
        with ChDir():
            readme = Path('test')/'readme.txt'
            readme.parent.mkdir()
            installer = PythonInstaller()
            self.assertFalse(installer.check_repo(Path.cwd()))
            self.assertFalse(installer.check_repo(Path.cwd()/'test'))
            with readme.open('w') as f:
                f.write('\n')
            self.assertTrue(readme.exists())
            self.assertFalse(installer.check_repo(Path.cwd()/'test'))

    def test_get_virtualenv_exists(self):
        with ChDir():  # Make sure theres no .env file when running tests
            installer = PythonInstaller()
            venv_path = Path('.venv')
            venv_path.mkdir()
            self.assertTrue(venv_path.exists())
            expected = self._get_executable_path(venv_path)
            self.assertEqual(installer._get_virtualenv(venv_path), expected.absolute())

    @patch.object(installer, 'virtualenv')
    def test_get_virtualenv_new(self, venv):
        with ChDir():  # Make sure theres no .env file when running tests
            installer = PythonInstaller()
            venv_path = Path('.venv')
            self.assertFalse(venv_path.exists())
            expected = self._get_executable_path(venv_path)
            self.assertEqual(installer._get_virtualenv(venv_path), expected.absolute())
            venv.cli_run.assert_called_once_with([str(venv_path)]+installer.virtualenv_args)

    @patch.object(installer, 'virtualenv')
    def test_get_virtualenv_new_args(self, venv):
        with ChDir():  # Make sure theres no .env file when running tests
            installer = PythonInstaller(virtualenv_args=['a', 'b'])
            venv_path = Path('.venv')
            self.assertFalse(venv_path.exists())
            expected = self._get_executable_path(venv_path)
            self.assertEqual(installer._get_virtualenv(venv_path), expected.absolute())
            venv.cli_run.assert_called_once_with([str(venv_path), 'a', 'b'])

    def test_get_executable_no_codebase(self):
        with ChDir():  # Make sure theres no .env file when running tests
            installer = PythonInstaller()
            venv_path = Path('.venv')
            venv_path.mkdir()
            expected = self._get_executable_path(venv_path)
            self.assertEqual(installer._get_executable(Path.cwd(), None, 'venv'), expected.absolute())

    def test_get_executable_root_virtualenv_dir(self):
        with ChDir():  # Make sure theres no .env file when running tests
            venv_path = Path('test', '.venv')
            venv_path.mkdir(parents=True)
            installer = PythonInstaller(virtualenv_dir=venv_path.absolute())
            expected = self._get_executable_path(venv_path)
            self.assertEqual(installer._get_executable(Path.cwd(), None, 'venv'), expected.absolute())

    def test_get_executable_no_venv(self):
        with ChDir():
            venv_path = Path('test', '.venv')
            venv_path.mkdir(parents=True)
            installer = PythonInstaller(virtualenv_dir=venv_path.absolute())
            self.assertEqual(installer._get_executable(Path.cwd(), None, None), sys.executable)

    def test_get_executable_custom(self):
        with ChDir():
            venv_path = Path('test', '.venv')
            venv_path.mkdir(parents=True)
            installer = PythonInstaller(virtualenv_dir=venv_path.absolute())
            self.assertEqual(installer._get_executable(Path.cwd(), None, 'abc'), 'abc')

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_setup_py_no_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('setup.py', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=False)
            sp.check_call.assert_called_once_with(['abc', '-m', 'pip', 'install', '-e', '.[dev]', '--no-deps'])

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_pyproject_toml_no_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('pyproject.toml', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=False)
            sp.check_call.assert_called_once_with(['abc', '-m', 'pip', 'install', '-e', '.[dev]', '--no-deps'])

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_requirements_txt_no_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('requirements.txt', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=False)
            sp.check_call.assert_not_called()

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_setup_py_no_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('setup.py', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=True)
            sp.check_call.assert_called_once_with(['abc', '-m', 'pip', 'install', '-e', '.[dev]'])

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_pyproject_toml_no_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('pyproject.toml', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=True)
            sp.check_call.assert_called_once_with(['abc', '-m', 'pip', 'install', '-e', '.[dev]'])

    @patch.object(installer, 'subprocess', autospec=True)
    def test_install_requirements_txt_deps(self, sp):
        with ChDir():
            installer = PythonInstaller()
            with open('requirements.txt', 'w') as f:
                f.write('\n')
            installer.install(Path.cwd(), executable='abc', deps=True)
            sp.check_call.assert_called_once_with(['abc', '-m', 'pip', 'install', '-r', 'requirements.txt'])

class PythonInstallerWithCodebaseTestCase(unittest.TestCase):
    # Codebase Tests

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
        return TestExtension('dummy', PROVIDER_ENTRYPOINT, self._provider_settings_cls)

    def env(self):
        return Env(override={'TEST_ABACUS': 'A'})

    def _get_executable_path(self, venv_path):
        if sys.platform.startswith('win'):
            expected = venv_path/'Scripts'/'python.exe'
        else:
            expected = venv_path/'bin'/'python'
        return expected

    @patch.object(RepoClient, '__abstractmethods__', set())
    def test_get_executable_codebase_root_dir(self):
        with ChDir():
            with self.extension():
                with self.env():
                    settings.ProviderEnum._patch()
                    c = Codebase()
                    venv_path = Path('.venv')
                    venv_path.mkdir()
                    test_path = Path('test', 'abc')
                    test_path.mkdir(parents=True)
                    installer = PythonInstaller()
                    expected = self._get_executable_path(venv_path)
                    self.assertEqual(installer._get_executable(Path.cwd(), None, 'venv'), expected.absolute())
