from pathlib import Path
import sys
from typing import Annotated, List, Optional

import virtualenv
from pydantic import Field, field_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration
from nskit.mixer import Recipe
from nskit.vcs.namespace_validator import NamespaceValidator
from nskit.vcs.repo import NamespaceValidationRepo, Repo
from nskit.vcs.settings import CodebaseSettings


class Codebase(BaseConfiguration):
    root_dir: Path = Field(default_factory=Path.cwd)
    settings: Annotated[CodebaseSettings, Field(validate_default=True)] = None
    namespaces_dir: Path = Path('.namespaces')
    virtualenv_dir: Path = Path('.venv')
    namespace_validation_repo: Optional[NamespaceValidationRepo] = None
    # Include Azure DevOps seeder
    virtualenv_args: List[str] = ['--seeder', 'azdo-pip']

    @field_validator('settings', mode='before')
    @classmethod
    def _validate_settings(cls, value):
        if value is None:
            value = CodebaseSettings()
        return value

    @field_validator('namespace_validation_repo', mode='before')
    @classmethod
    def _validate_namespace_validation_repo_from_settings(cls, value, info: ValidationInfo):
        if value is None:
            value = info.data.get('settings').namespace_validation_repo
        return value

    @field_validator('namespace_validation_repo', mode='after')
    @classmethod
    def _validate_namespace_validation_repo(cls, value, info: ValidationInfo):
        if value:
            value.local_dir = info.data.get('root_dir')/info.data.get('namespaces_dir')
        return value

    def __post_init__(self):
        self.settings.namespace_validation_repo = self.namespace_validation_repo

    @property
    def _full_virtualenv_dir(self):
        return self.root_dir/self.virtualenv_dir

    @property
    def namespace_validator(self):
        if self.namespace_validation_repo:
            return self.namespace_validation_repo.validator
        else:
            return NamespaceValidator(options=None)

    def list_repos(self):
        # Get the repo names that are validated by the namespace_validator
        potential_repos = self.settings.provider_settings.repo_client.list()
        sdk_repos = []
        for repo in potential_repos:
            result, _ = self.namespace_validator.validate_name(repo)
            if result:
                sdk_repos.append(repo)
        return sdk_repos

    @property
    def virtualenv(self):
        # Context manager for the virtualenv (create it if it doesn't exist)
        # Ideally we would use azure_devops_artifacts_helpers here to ensure the virtualenv is seeded etc.
        # How do we ensure installation (let's not worry, as we also need this package as well...)
        if not self._full_virtualenv_dir.exists():
            virtualenv.cli_run([str(self._full_virtualenv_dir)]+self.virtualenv_args)
        if sys.platform.startswith('win'):
            executable = self._full_virtualenv_dir/'Scripts'/'python.exe'
        else:
            executable = self._full_virtualenv_dir/'bin'/'python'
        return executable.absolute()

    def clone(self):
        # List repos
        root = self.root_dir
        root.mkdir(exist_ok=True, parents=True)
        repos = self.list_repos()
        # Create folder structure based on namespacing
        cloned = []
        for repo in repos:
            repo_dir = self.root_dir/Path(*self.namespace_validator.to_parts(repo))
            r = Repo(
                name=repo,
                local_dir=repo_dir,
                namespace_validation_repo=self.namespace_validation_repo,
                validation_level=self.settings.validation_level,
                provider_client=self.settings.provider_settings.repo_client)
            if not r.exists_locally:
                r.clone()
            r.install(executable=self.virtualenv, deps=False)
            cloned.append(r)
        # Once installed all with no deps, install deps again
        for repo in cloned:
            r.install(executable=self.virtualenv, deps=True)
        return cloned

    def create_repo(self, name, with_recipe: Optional[str] = None, **recipe_kwargs):
        repo_dir = self.root_dir/Path(*self.namespace_validator.to_parts(name))
        r = Repo(
            name=name,
            local_dir=repo_dir,
            namespace_validation_repo=self.namespace_validation_repo,
            validation_level=self.settings.validation_level,
            provider_client=self.settings.provider_settings.repo_client)
        if r.exists or r.exists_locally:
            raise ValueError(f'Repo {name} already exists')
        r.create()
        if with_recipe is not None:
            repo = recipe_kwargs.get('repo', {})
            repo['url'] = repo.get('url', r.url)
            recipe_kwargs['repo'] = repo
            recipe = Recipe.load(
                with_recipe,
                name='.'.join(self.namespace_validator.to_parts(r.name)),
                **recipe_kwargs
            )
            recipe.create(
                base_path=r.local_dir.parent,
                override_path=self.namespace_validator.to_parts(r.name)[-1]
            )
            r.commit('Initial commit', hooks=False)
            r.push()
            r.install(executable=self.virtualenv, deps=True)

    def delete_repo(self, name):
        repo_dir = self.root_dir/Path(*self.namespace_validator.to_parts(name))
        r = Repo(
            name=name,
            local_dir=repo_dir,
            namespace_validation_repo=self.namespace_validation_repo,
            validation_level=self.settings.validation_level,
            provider_client=self.settings.provider_settings.repo_client)
        r.delete()
