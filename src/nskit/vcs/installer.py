"""Repository installers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import subprocess  # nosec B404
import sys
from typing import List, TYPE_CHECKING

from pydantic_settings import SettingsConfigDict
import virtualenv

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers import ChDir
from nskit.common.extensions import ExtensionsEnum

if TYPE_CHECKING:
    from nskit.vcs.codebase import Codebase


logger = logger_factory.get_logger(__name__)

ENTRYPOINT = 'nskit.vcs.installers'
InstallersEnum = ExtensionsEnum.from_entrypoint('InstallersEnum', ENTRYPOINT)


class Installer(ABC, BaseConfiguration):
    """Abstract class for language installer.

    Can be enabled or disabled using the boolean flag and environment variables.
    """

    enabled: bool = True

    def check(self, path: Path, **kwargs):
        """Check if the installer is enabled, and the repo matches the criteria."""
        return self.enabled and self.check_repo(path=path, **kwargs)

    @abstractmethod
    def check_repo(self, path: Path, **kwargs):
        """Check if the repo matches the installer language."""
        raise NotImplementedError('Implement in a language specific installer. It should check for appropriate files to signal that it is a repo of that type')

    @abstractmethod
    def install(self, path: Path, *, codebase: Codebase | None = None, deps: bool = True, **kwargs):
        """Install the repo into the appropriate environment."""
        raise NotImplementedError('Implement in language specific installer. It should take in any language specific environment/executables')


class PythonInstaller(Installer):
    """Python language installer.

    Can be enabled or disabled using the boolean flag and environment variables. The virtualenv config can be updated (to a custom dir/path relative to the codebase root)
    """

    model_config = SettingsConfigDict(env_prefix='NSKIT_PYTHON_INSTALLER_', env_file='.env')
    virtualenv_dir: Path = Path('.venv')
    # Include Azure DevOps seeder
    virtualenv_args: List[str] = []
    # For Azure Devops could set this to something like: ['--seeder', 'azdo-pip']

    def check_repo(self, path: Path):
        """Check if this is a python repo."""
        logger.debug(f'{self.__class__} enabled, checking for match.')
        result = (path/'setup.py').exists() or (path/'pyproject.toml').exists() or (path/'requirements.txt').exists()
        logger.info(f'Matched repo to {self.__class__}.')
        return result

    def install(self, path: Path, *, codebase: Codebase | None = None, executable: str = 'venv', deps: bool = True):
        """Install the repo.

        executable can override the executable to use (e.g. a virtualenv)
        deps controls whether dependencies are installed or not.
        """
        executable = self._get_executable(path, codebase, executable)
        logger.info(f'Installing using {executable}.')
        args = []
        if not deps:
            args.append('--no-deps')
        with ChDir(path):
            if Path('setup.py').exists() or Path('pyproject.toml').exists():
                subprocess.check_call([str(executable), '-m', 'pip', 'install', '-e', '.[dev]']+args)  # nosec B603, B607
            elif deps and Path('requirements.txt').exists():
                subprocess.check_call([str(executable), '-m', 'pip', 'install', '-r', 'requirements.txt'])  # nosec B603, B607

    def _get_virtualenv(self, full_virtualenv_dir: Path):
        """Get the virtualenv executable.

        Create's it if it doesn't exist.
        """
        if not full_virtualenv_dir.exists():
            virtualenv.cli_run([str(full_virtualenv_dir)]+self.virtualenv_args)
        if sys.platform.startswith('win'):
            executable = full_virtualenv_dir/'Scripts'/'python.exe'
        else:
            executable = full_virtualenv_dir/'bin'/'python'
        return executable.absolute()

    def _get_executable(self, path: Path, codebase: Codebase | None = None, executable: str | None = 'venv'):
        # Install in the current environment
        if self.virtualenv_dir.is_absolute():
            full_virtualenv_dir = self.virtualenv_dir
        elif codebase:
            full_virtualenv_dir = codebase.root_dir/self.virtualenv_dir
        else:
            full_virtualenv_dir = path/self.virtualenv_dir
        if executable is None:
            executable = sys.executable
        elif executable == 'venv':
            executable = self._get_virtualenv(full_virtualenv_dir=full_virtualenv_dir)
        return executable
