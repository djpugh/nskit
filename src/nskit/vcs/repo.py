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
from pydantic import Field, field_validator, model_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration
from nskit.common.contextmanagers import ChDir
from nskit.common.io import yaml
from nskit.vcs.namespace_validator import NamespaceOptionsType, NamespaceValidator, ValidationEnum
from nskit.vcs.providers import RepoClient


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
        return self.provider_client.get_remote_url(self.name)

    def create(self):
        if not self.exists:
            self.provider_client.create(self.name)
        self.clone()

    def delete(self, remote=True):
        if self.exists_locally:
            shutil.rmtree(self.local_dir)
        if remote and self.exists:
            self.provider_client.delete(self.name)

    def clone(self):
        if not self.exists_locally:
            if not self.local_dir.parent.exists():
                self.local_dir.parent.mkdir(exist_ok=True)
            if self.url:
                self._git_repo_cls.clone_from(url=self.url, to_path=str(self.local_dir))

    def pull(self, remote=DEFAULT_REMOTE):
        # This will use python git library
        getattr(self._git_repo.remotes, remote).pull()

    def commit(self, message: str, paths: Union[List[Union[str, Path]], Union[str, Path]] = '*', hooks=True):
        # Because GitPython add cannot be set to use the .gitignore, we use subprocess here
        if not(isinstance(paths, (list, tuple))):
            paths = [paths,]
        with ChDir(self._git_repo.working_tree_dir):
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
                self._git_repo.create_head(branch).checkout()
            else:
                raise e from None

    def fetch(self, remote=DEFAULT_REMOTE):
        getattr(self._git_repo.remotes, remote).fetch()

    @property
    def _git_repo(self):
        if self.__git_repo is None or Path(self.__git_repo.working_tree_dir) != self.local_dir:
            self.__git_repo = self._git_repo_cls(self.local_dir)
        return self.__git_repo

    @property
    def exists_locally(self):
        return self.local_dir.exists() and (self.local_dir/'.git').exists()

    @property
    def exists(self):
        return self.provider_client.check_exists(self.name)

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
    namespaces_filename: Union[str, Path] = 'namespaces.yaml'
    local_dir: Annotated[Path, Field(validate_default=True)] = None

    _validator: NamespaceValidator = None

    @property
    def validator(self):
        if self._validator is None:
            self._validator = self._load_namespace_validator()
        return self._validator

    def validate_name(self, proposed_name):
        return self.validator.validate_name(proposed_name)

    # Validate default for local_dir
    @field_validator('local_dir', mode='before')
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
            namespace_options: Union[NamespaceOptionsType, NamespaceValidator],
            delimiters: Optional[List[str]] = None,
            repo_separator: Optional[str] = None):
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
                warnings.warn(message)
        self.name = value
