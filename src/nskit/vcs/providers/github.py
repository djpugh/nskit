
from pydantic_settings import HttpUrl, SettingsConfigDict

from nskit.vcs.providers._base import RepoClient, VCSProviderSettings


class GithubSettings(VCSProviderSettings):
    model_config = SettingsConfigDict(env_prefix='GITHUB_', env_file='.env')
    url: HttpUrl = "https://github.com"
    organisation: str

    @property
    def organisation_url(self):
        return f'{self.url}/{self.organisation}'

    @property
    def repo_client(self) -> 'GithubRepoClient':
        return GithubRepoClient(self)


class GithubRepoClient(RepoClient):

    def __init__(self, config: GithubSettings):
        self._config = config
