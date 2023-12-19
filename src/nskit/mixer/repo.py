"""A base recipe object for a code (git) repo."""
from typing import Callable, List, Optional

from pydantic import EmailStr, Field, HttpUrl

from nskit.common.configuration import BaseConfiguration
from nskit.mixer import hooks
from nskit.mixer.components import LicenseOptionsEnum, Recipe


class GitConfig(BaseConfiguration):
    """Git Configuration for the Git Repo."""

    initial_branch_name: str = 'main'
    git_flow: bool = True

    @property
    def default_branch(self):
        """Get the default branch."""
        if self.git_flow:
            return 'develop'
        else:
            return self.initial_branch_name


class RepoMetadata(BaseConfiguration):
    """Repository/package metadata information."""

    repo_separator: str = '-'
    owner: str = Field(..., description="Who is the owner of the repo")
    email: EmailStr = Field(..., description="The email for the repo owner")
    description: str = Field('', description="A summary description for the repo")
    url: HttpUrl = Field(..., description='The Repository url.')


class CodeRecipe(Recipe):
    """Recipe for a code repo.

    Includes default git init and precommit install hooks.
    """
    repo: RepoMetadata
    post_hooks: Optional[List[Callable]] = Field(
        [hooks.git.GitInit(), hooks.pre_commit.PrecommitInstall()],
        validate_default=True,
        description='Hooks that can be used to modify a recipe path and context after writing'
    )
    git: GitConfig = GitConfig()
    language: str = 'python'
    license: Optional[LicenseOptionsEnum] = None

    def get_pipeline_filenames(self):
        """Get CICD Pipeline filenames."""
        return []
