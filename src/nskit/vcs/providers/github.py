"""Github provider using PyGithub."""
from typing import List, Optional

try:
    from github import Github, UnknownObjectException
    from github.Auth import Token
except ImportError:
    raise ImportError('Github Provider requires installing extra dependencies, use pip install nskit[github]')
from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import SettingsConfigDict

from nskit.common.configuration import BaseConfiguration
from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings


class GithubRepoSettings(BaseConfiguration):
    """Github Repo settings."""
    private: bool = True
    has_issue: Optional[bool] = None
    has_wiki: Optional[bool] = None
    has_downloads: Optional[bool] = None
    has_projects: Optional[bool] = None
    allow_squash_merge: Optional[bool] = None
    allow_merge_commit: Optional[bool] = None
    allow_rebase_merge: Optional[bool] = None
    delete_branch_on_merge: Optional[bool] = None
    auto_init: bool = False


class GithubSettings(VCSProviderSettings):
    """Github settings.

    Uses PAT token for auth (set in environment variables as GITHUB_TOKEN)
    """
    model_config = SettingsConfigDict(env_prefix='GITHUB_', env_file='.env')
    url: HttpUrl = "https://github.com"
    organisation: Optional[str] = Field(None, description='Organisation to work in, otherwise uses the user for the token')
    token: SecretStr
    repo: GithubRepoSettings = GithubRepoSettings()

    @property
    def repo_client(self) -> 'GithubRepoClient':
        """Get the instantiated repo client."""
        return GithubRepoClient(self)


class GithubRepoClient(RepoClient):
    """Client for managing github repos."""

    def __init__(self, config: GithubSettings):
        """Initialise the client."""
        self._config = config
        self._github = Github(
            auth=Token(self._config.token.get_secret_value()),
            base_url=self._config.url
            )
        # If the organisation is set, we get it, and assume that the token is valid
        # Otherwise default to the user
        if self._config.organisation:
            self._org = self._github.get_organization(self._config.organisation)
        else:
            self._org = self._github.get_user()

    def create(self, repo_name: str):
        """Create the repo in the user/organisation."""
        return self._org.create_repo(
            name=repo_name,
            private=self._config.repo.private,
            has_issues=self._config.repo.has_issues,
            has_wiki=self._config.repo.has_wiki,
            has_downloads=self._config.repo.has_downloads,
            has_projects=self._config.repo.has_projects,
            allow_squash_merge=self._config.repo.allow_squash_merge,
            allow_merge_commit=self._config.repo.allow_merge_commit,
            allow_rebase_merge=self._config.repo.allow_rebase_merge,
            auto_init=self._config.repo.auto_init,
            delete_branch_on_merge=self._config.repo.delete_branch_on_merge
        )

    def get_remote_url(self, repo_name: str) -> HttpUrl:
        """Get the remote url for the repo."""
        if self.check_exists(repo_name):
            return self._org.get_repo(repo_name).clone_url

    def delete(self, repo_name: str):
        """Delete the repo if it exists in the organisation/user."""
        if self.check_exists(repo_name):
            return self._org.get_repo(repo_name).delete()

    def check_exists(self, repo_name: str) -> bool:
        """Check if the repo exists in the organisation/user."""
        try:
            self._org.get_repo(repo_name)
            return True
        except UnknownObjectException:
            return False

    def list(self) -> List[str]:
        """List the repos in the project."""
        return [u.name for u in self._org.get_repos()]
