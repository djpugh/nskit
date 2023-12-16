"""Manage a codebase."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import List, Optional

if sys.version_info.major <= 3 and sys.version_info.minor <= 8:
    from typing_extensions import Annotated
else:
    from typing import Annotated

from pydantic import Field, field_validator, ValidationInfo

from nskit.common.configuration import BaseConfiguration
from nskit.mixer import Recipe
from nskit.vcs.namespace_validator import NamespaceValidator
from nskit.vcs.repo import NamespaceOptionsType, NamespaceValidationRepo, Repo
from nskit.vcs.settings import CodebaseSettings


class Codebase(BaseConfiguration):
    """Object for managing a codebase."""
    root_dir: Path = Field(default_factory=Path.cwd)
    settings: Annotated[CodebaseSettings, Field(validate_default=True)] = None
    namespaces_dir: Path = Path('.namespaces')
    namespace_validation_repo: Optional[NamespaceValidationRepo] = None

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
            try:
                value = info.data.get('settings').namespace_validation_repo
            except (AttributeError) as e:
                raise ValueError(e) from None
        return value

    @field_validator('namespace_validation_repo', mode='after')
    @classmethod
    def _validate_namespace_validation_repo(cls, value, info: ValidationInfo):
        if value:
            value.local_dir = info.data.get('root_dir')/info.data.get('namespaces_dir')
        return value

    def model_post_init(self, *args, **kwargs):
        """Set the settings namespace validation repo to the same as the codebase."""
        super().model_post_init(*args, **kwargs)
        self.settings.namespace_validation_repo = self.namespace_validation_repo

    @property
    def namespace_validator(self):
        """Get the namespace validator object."""
        if self.namespace_validation_repo:
            return self.namespace_validation_repo.validator
        else:
            return NamespaceValidator(options=None)

    def list_repos(self):
        """Get the repo names that are validated by the namespace_validator if provided."""
        potential_repos = self.settings.provider_settings.repo_client.list()
        sdk_repos = []
        for repo in potential_repos:
            result, _ = self.namespace_validator.validate_name(repo)
            if result:
                sdk_repos.append(repo)
        return sdk_repos

    def clone(self):
        """Clone all repos that match the codebase to a local (nested) directory."""
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
            r.install(codebase=self, deps=False)
            cloned.append(r)
        # Once installed all with no deps, install deps again
        for repo in cloned:
            repo.install(codebase=self, deps=True)
        return cloned

    def create_repo(self, name, with_recipe: Optional[str] = None, **recipe_kwargs):
        """Create a repo in the codebase.

        with_recipe will instantiate it with a specific recipe - the kwargs need to be provided to the call.
        """
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
            repo['repo_separator'] = repo.get('repo_separator', self.namespace_validator.repo_separator)
            recipe_kwargs['repo'] = repo
            recipe = Recipe.load(
                with_recipe,
                name=repo['repo_separator'].join(self.namespace_validator.to_parts(r.name)),
                **recipe_kwargs
            )
            created = recipe.create(
                base_path=r.local_dir.parent,
                override_path=self.namespace_validator.to_parts(r.name)[-1]
            )
            r.commit('Initial commit', hooks=False)
            r.push()
            r.install(codebase=self, deps=True)
            return created

    def delete_repo(self, name):
        """Delete a repo from the codebase."""
        repo_dir = self.root_dir/Path(*self.namespace_validator.to_parts(name))
        r = Repo(
            name=name,
            local_dir=repo_dir,
            namespace_validation_repo=self.namespace_validation_repo,
            validation_level=self.settings.validation_level,
            provider_client=self.settings.provider_settings.repo_client)
        r.delete()

    def create_namespace_repo(
            self,
            name: str | None = None,
            *,
            namespace_options: NamespaceOptionsType | NamespaceValidator,
            delimiters: List[str] | None = None,
            repo_separator: str | None = None,
            namespaces_filename: str | Path = 'namespaces.yaml'):
        """Create and populate the validator repo."""
        if name is None:
            name = self.namespaces_dir.name
        self.namespace_validation_repo = NamespaceValidationRepo(
            name=name,
            namespaces_filename=namespaces_filename,
            local_dir=self.namespaces_dir
        )
        self.namespace_validation_repo.create(
            namespace_options=namespace_options,
            delimiters=delimiters,
            repo_separator=repo_separator
        )
