"""Repo management class."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from typing import Any, Optional, TYPE_CHECKING, Union
import warnings

if sys.version_info.major <= 3 and sys.version_info.minor <= 8:
    from typing_extensions import Annotated
else:
    from typing import Annotated

import git
from pydantic import Field, field_validator, model_validator, ValidationInfo

from nskit._logging import logger_factory
from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers import ChDir
from nskit.common.io import yaml
from nskit.vcs.installer import InstallersEnum
from nskit.vcs.namespace_validator import (
    NamespaceOptionsType,
    NamespaceValidator,
    ValidationEnum,
)
from nskit.vcs.providers import RepoClient

if TYPE_CHECKING:
    from nskit.vcs.codebase import Codebase


logger = logger_factory.get_logger(__name__)


DEFAULT_REMOTE = 'origin'
# We should set the default dir in some form of env var/other logic in the cli

_NAMESPACE_README = """
# {name}

Contains the approved namespaces as a `YAML` file - `namspaces.yaml`

This is structured as a YAML object, with the options as a list of dictionary lists, with the approved roots at L0, approved L1s etc.

e.g.
```
options:
    - x:
        - y:
            - a
            - b
        - z:
            - w
        - q
delimiters:
    - -
    - .
    - ,
repo_separator: -
```

Means we can have repos structured as:
```
- x-y-a-<*>
- x-y-b-<*>
- x-z-w-<*>
- x-q-<*>
```
but no others.

The separator is set by the repo_separator parameter, in this example "-".
"""  # noqa: E800


class _Repo(BaseConfiguration):

    name: str
    local_dir: Path = Field(default_factory=Path.cwd)
    default_branch: str = 'main'
    provider_client: Annotated[RepoClient, Field(validate_default=True)] = None

    __git_repo = None
    _git_repo_cls = git.Repo

    @field_validator('provider_client', mode='before')
    @classmethod
    def _validate_client(cls, value):
        if value is None:
            from nskit.vcs.settings import CodebaseSettings
            value = CodebaseSettings().provider_settings.repo_client
        return value

    @property
    def url(self):
        """Get the remote url."""
        return self.provider_client.get_remote_url(self.name)

    @property
    def clone_url(self):
        """Get the remote url."""
        return self.provider_client.get_clone_url(self.name)

    def create(self):
        """Create the repo."""
        if not self.exists:
            self.provider_client.create(self.name)
        self.clone()
        if not self.exists_locally:
            self.local_dir.mkdir(exist_ok=True, parents=True)
            with ChDir(self.local_dir):
                self._git_repo_cls.init()

    def delete(self, remote=True):
        """Delete the repo.

        remote=True (default), deletes the repo on the remote (no confirmation).
        """
        if remote and self.exists:
            self.provider_client.delete(self.name)
        if self.exists_locally:
            errors = []

            def on_exc(function, path, exc_info):  # noqa: U100
                """Log errors when deleting."""
                errors.append((path, exc_info))
            if sys.version_info.major <= 3 and sys.version_info.minor < 12:
                shutil.rmtree(self.local_dir, onerror=on_exc)
            else:
                shutil.rmtree(self.local_dir, onexc=on_exc)
            if errors:
                error_info = "\n".join([str(u) for u in errors])
                warnings.warn(f'Unable to delete some paths due to errors:\n{error_info}', stacklevel=2)

    def clone(self):
        """Clone the repo."""
        if not self.exists_locally:
            if not self.local_dir.parent.exists():
                self.local_dir.parent.mkdir(exist_ok=True, parents=True)
            if self.clone_url:
                self._git_repo_cls.clone_from(url=self.clone_url, to_path=str(self.local_dir))

    def pull(self, remote=DEFAULT_REMOTE):
        """Pull the repo from the remote (defaults to origin)."""
        # This will use python git library
        if self._git_repo.remotes:
            getattr(self._git_repo.remotes, remote).pull()
        else:
            warnings.warn('No Remotes found', stacklevel=2)

    def commit(self, message: str, paths: list[str | Path] | str | Path = '*', hooks=True):
        """Commit the paths with given message.

        hooks=False disables running pre-commit hooks.
        """
        # Because GitPython add cannot be set to use the .gitignore, we use subprocess here
        if not isinstance(paths, (list, tuple)):
            paths = [paths,]
        with ChDir(self._git_repo.working_tree_dir):
            subprocess.check_call(['git', 'add']+paths)  # nosec B603, B607
            if hooks:
                hook_args = []
            else:
                hook_args = ['--no-verify']
            subprocess.check_call(['git', 'commit'] + hook_args + ['-m', message])  # nosec B603, B607

    def push(self, remote=DEFAULT_REMOTE):
        """Push the repo to the remote (defaults to origin)."""
        if self._git_repo.remotes:
            getattr(self._git_repo.remotes, remote).push()
        else:
            warnings.warn('No Remotes found', stacklevel=2)

    def tag(self, tag, message: str | None = None, force: bool = False):
        """Tag the repo (with a given name, and optional message."""
        self._git_repo.create_tag(tag, message=message, force=force)

    def checkout(self, branch, create=True):
        """Checkout the branch (create if true)."""
        self.fetch()
        try:
            getattr(self._git_repo.heads, branch).checkout()
        except AttributeError as e:
            if create:
                self._git_repo.create_head(branch).checkout()
            else:
                raise e from None

    def fetch(self, remote=DEFAULT_REMOTE):
        """Fetch the repo from the remote (defaults to origin)."""
        getattr(self._git_repo.remotes, remote).fetch()

    @property
    def _git_repo(self):
        if self.__git_repo is None or Path(self.__git_repo.working_tree_dir) != self.local_dir:
            self.__git_repo = self._git_repo_cls(self.local_dir)
        return self.__git_repo

    @property
    def exists_locally(self):
        """Check if the repo exists locally (and .git initialised)."""
        return self.local_dir.exists() and (self.local_dir/'.git').exists()

    @property
    def exists(self):
        """Check if the repo exists on the remote."""
        return self.provider_client.check_exists(self.name)

    def install(self, codebase: Codebase | None = None, deps: bool = True):
        """Install the repo into a codebase.

        To make it easy to extend to new languages/installation methods, this uses an entrypoint to handle it.

        The default installer is for python (uses a virtualenv), but can be disabled using NSKIT_PYTHON_INSTALLER_ENABLED=False if you
        want to provide a custom Python Installer (e.g. using poetry or hatch).

        Other installers can be added through the nskit.vcs.installers entry_point.
        """
        # Loop through available installers and check - if they check True, then install them
        for installer in InstallersEnum:
            logger.info(f'Trying {installer.value}, all matching languages will be installed.')
            if installer.extension:
                language_installer = installer.extension()
                if language_installer.check(self.local_dir):
                    logger.info(f'Matched {installer.value}, installing.')
                    language_installer.install(path=self.local_dir, codebase=codebase, deps=deps)


class NamespaceValidationRepo(_Repo):
    """Repo for managing namespace validation."""
    name: str = '.namespaces'
    namespaces_filename: Union[str, Path] = 'namespaces.yaml'
    local_dir: Annotated[Path, Field(validate_default=True)] = None

    _validator: NamespaceValidator = None

    @property
    def validator(self):
        """Get the namespace validator."""
        if self._validator is None:
            self._validator = self._load_namespace_validator()
        return self._validator

    def validate_name(self, proposed_name: str):
        """Validate the proposed name."""
        return self.validator.validate_name(proposed_name)

    # Validate default for local_dir
    @field_validator('local_dir', mode='before')
    @classmethod
    def _validate_local_dir(cls, value: Any, info: ValidationInfo):
        if value is None:
            value = Path(tempfile.tempdir)/info.data['name']
        return value

    def _download_namespaces(self):
        # Into a .namespaces "hidden" directory that we check and pull if necessary
        self.clone()
        self.checkout(self.default_branch)

    def _load_namespace_validator(self):
        if not self.exists_locally:
            self._download_namespaces()
        self.pull()
        with (self.local_dir/self.namespaces_filename).open() as f:
            namespace_validator = NamespaceValidator(**yaml.load(f))
        return namespace_validator

    def create(
            self,
            *,
            namespace_options: NamespaceOptionsType | NamespaceValidator,
            delimiters: list[str] | None = None,
            repo_separator: str | None = None):
        """Create and populate the validator repo."""
        # Provide either namespace_validator or namespaceOptions
        kwargs = {}
        if delimiters:
            kwargs['delimiters'] = delimiters
        if repo_separator:
            kwargs['repo_separator'] = repo_separator
        if not isinstance(namespace_options, NamespaceValidator):
            namespace_validator = NamespaceValidator(
                options=namespace_options,
                **kwargs
                )
        else:
            # namespace_options is a NamespaceValidator
            namespace_validator = namespace_options.model_copy(update=kwargs)
        # Create the repo
        super().create()
        with ChDir(self.local_dir):
            # Write the Config
            with open(self.namespaces_filename, 'w') as f:
                f.write(namespace_validator.model_dump_yaml())
            with open('README.md', 'w') as f:
                f.write(_NAMESPACE_README)
            # Commit it
            self.commit('Initial Namespaces Commit', [self.namespaces_filename, 'README.md'])
            # Push it
            self.push()


class Repo(_Repo):
    """Repo with namespace validator."""

    namespace_validation_repo: Optional[NamespaceValidationRepo] = None
    validation_level: ValidationEnum = ValidationEnum.none
    name: str

    @model_validator(mode='after')
    def _validate_name(self):
        value = self.name
        if self.namespace_validation_repo and self.validation_level in [ValidationEnum.strict, ValidationEnum.warn]:
            namespace_validator = self.namespace_validation_repo.validator
            result, message = namespace_validator.validate_name(value)
            if not result:
                message = (f'{value} {message.format(key="<root>")}')
            value = namespace_validator.to_repo_name(value)
            if self.validation_level == ValidationEnum.strict and not result:
                raise ValueError(message)
            elif not result:
                warnings.warn(message, stacklevel=2)
        self.name = value
