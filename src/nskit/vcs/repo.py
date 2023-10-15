from __future__ import annotations
from enum import Enum
import glob
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Annotated, Any, List, Optional, Sequence, Union
import warnings

import git
from pydantic import Field, field_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers import ChDir
from nskit.common.io import yaml
from nskit.vcs.namespace_validator import NamespaceOptionsType, NamespaceValidator
from nskit.vcs.providers import RepoClient
from nskit.vcs.settings import SDKSettings


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
"""


class _Repo(BaseConfiguration):

    local_dir: Path = Field(default_factory=Path.cwd)
    default_branch: str = 'main'
    provider_client: Annotated[RepoClient, Field(validate_default=True)] = None
    name: str

    __git_repo = None

    @field_validator('provider_client')
    @classmethod
    def _validate_client(cls, value):
        if value is None:
            value = SDKSettings().provider_settings.get_repo_client()
        return value

    @property
    def url(self):
        return self._client.get_remote_url(self.name)

    def create(self):
        if not self.exists:
            self._client.create(self.name)
        self.clone()

    def delete(self, remote=True):
        if self.exists_locally:
            shutil.rmtree(self.local_dir)
        if remote and self.exists:
            self._client.delete(self.name)

    def clone(self):
        if not self.exists_locally:
            if not self.local_dir.parent.exists():
                self.local_dir.parent.mkdir(exist_ok=True)
            if self.url:
                git.Repo.clone_from(url=self.url, to_path=str(self.local_dir))

    def pull(self, remote=DEFAULT_REMOTE):
        # This will use python git library
        getattr(self._git_repo.remotes, remote).pull()

    def commit(self, message: str, paths: Union[List[Union[str, Path]], Union[str, Path]] = '*', hooks=True):
        # Because GitPython add cannot be set to use the .gitignore, we use subprocess here
        if not(isinstance(paths, (Sequence))):
            paths = [paths,]
        with ChDir(self.__git_repo.working_dir):
            subprocess.check_call(['git', 'add']+paths)
            if hooks:
                hook_args = []
            else:
                hook_args = ['--no-verify']
            subprocess.check_call(['git', 'commit'] + hook_args + ['-m', message])

    def push(self, remote=DEFAULT_REMOTE):
        getattr(self._git_repo.remotes, remote).push()

    def tag(self, tag, message: Optional[str] = None, force: bool = False):
        self._git_repo.create_tag(tag, message=message, force=force)

    def checkout(self, branch, create=True):
        self.fetch()
        try:
            getattr(self._git_repo.heads, branch).checkout()
        except AttributeError as e:
            if create:
                self._git_repo.create_head(branch)
            else:
                raise e from None

    def fetch(self, remote=DEFAULT_REMOTE):
        getattr(self._git_repo.remotes, remote).fetch()

    @property
    def _git_repo(self):
        if self.__git_repo is None or Path(self.__git_repo.working_dir) != self.local_dir:
            if not self.exists_locally:
                self.clone()
            self.__git_repo = git.Repo(self.local_dir)
        return self.__git_repo

    @property
    def exists_locally(self):
        return self.local_dir.exists() and (self.local_dir/'.git').exists()

    @property
    def exists(self):
        return self._client.check_exists(self.name)

    def install(self, executable=None, deps=True):
        # Install in the current environment
        if executable is None:
            executable = sys.executable
        args = []
        if not deps:
            args.append('--no-deps')
        with ChDir(self.local_dir):
            if (self.local_dir/'setup.py').exists() or (self.local_dir/'pyproject.toml').exists():
                subprocess.check_call([str(executable), '-m', 'pip', 'install', '-e', '.[dev]']+args)
            elif deps and (self.local_dir/'requirements.txt').exists():
                subprocess.check_call([str(executable), '-m', 'pip', 'install', 'requirements.txt'])


class NamespaceValidationRepo(_Repo):
    namespaces_filename='namespaces.yaml',
    storage_dir: Annotated[Path, Field(validate_default=True)] = None

    _validator = None

    @property
    def validator(self):
        if self._validator is None:
            self._validator = self._load_namespace_validator()
        return self._validator

    def validate_name(self, proposed_name):
        return self.validator.validate_name(proposed_name)

    # Validate default for storage_dir
    @field_validator('storage_dir', mode='before')
    def _validate_storage_dir(cls, value: Any, info: ValidationInfo):
        if value is None:
            value = Path(tempfile.tempdir())/info.data['name']

    def _download_namespaces(self):
        # Into a .namespaces "hidden" directory that we check and pull if necessary
        self.clone()
        self.checkout(self.default_branch)

    def _load_namespace_validator(self):
        if not self.exists_locally:
            self._download_namespaces()
        self.pull()
        with (self.local_dir/self._namespaces_filename).open() as f:
            namespace_validator = NamespaceValidator(**yaml.load(f))
        return namespace_validator

    def create(
            self,
            *,
            namespace_options: Union[NamespaceOptionsType, NamespaceValidator],
            delimiters: Optional[List[str]] = None,
            repo_separator: Optional[str] = None):
        # Provide either namespace_validator or namespaceOptions
        kwargs = {}
        if delimiters:
            kwargs['delimiters'] = delimiters
        if delimiters:
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
        self.create()
        # Write the Config
        with open(self.namespaces_filename, 'w') as f:
            f.write(namespace_validator.model_dump_yaml())
        with open('README.md', 'w') as f:
            f.write(_NAMESPACE_README)
        # Commit it
        self.commit('Initial Namespaces Commit', [self.namespace_filename, 'README.md'])
        # Push it
        self.push()


class ValidationEnum(Enum):
    strict = 2
    warn = 1
    none = 0


class Repo(_Repo):

    namespace_validation_repo: Optional[NamespaceValidationRepo] = None
    validation_level: ValidationEnum = ValidationEnum.none
    name: str

    @field_validator('name', mode='after')
    @classmethod
    def _validate_name(cls, value: str, info: ValidationInfo):
        namespace_validation_repo = info.data.get('namespace_validation_repo', None)
        validation_level = info.data.get('validation_level', ValidationEnum.none)
        if namespace_validation_repo and validation_level in [ValidationEnum.strict, ValidationEnum.warn]:
            namespace_validator = namespace_validation_repo.validator
            result, message = namespace_validator.validate_name(value)
            if not result:
                message = (f'{value} {message.format(key="<root>")}')
            value = namespace_validator.to_repo_name(value)
            if validation_level == ValidationEnum.strict and not result:
                raise ValueError(message)
            elif not result:
                warnings.warn(message)
        return value
