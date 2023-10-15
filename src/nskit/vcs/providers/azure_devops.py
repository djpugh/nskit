"""Azure Devops provider using azure-cli to manage it."""
from io import StringIO
import json
from typing import List

try:
    from azure.cli.core import get_default_cli
except ImportError:
    raise ImportError('Azure Devops Provider requires installing extra dependencies, use pip install nskit[azure_devops]')

from pydantic import HttpUrl
from pydantic_settings import SettingsConfigDict

from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings

# Want to use MS interactive Auth as default, but can't get it working, instead, using cli invoke


class AzureDevOpsSettings(VCSProviderSettings):
    """Azure DevOps settings."""
    model_config = SettingsConfigDict(env_prefix='AZURE_DEVOPS_', env_file='.env')
    url: HttpUrl = "https://dev.azure.com"
    organisation: str
    project: str

    @property
    def organisation_url(self):
        """Get the organistion Url."""
        return f'{self.url}/{self.organisation}'

    @property
    def project_url(self):
        """Get the project url."""
        return f'{self.organisation_url}/{self.project}'

    @property
    def repo_client(self) -> 'AzureDevOpsRepoClient':
        """Get the instantiated repo client."""
        return AzureDevOpsRepoClient(self)


class AzureDevOpsRepoClient(RepoClient):
    """Client for managing Azure DevOps repos using azure-cli."""

    def __init__(self, config: AzureDevOpsSettings):
        """Initialise the client."""
        self._cli = get_default_cli()
        self._config = config

    def _invoke(self, command, out_file=None):
        return self._cli.invoke(command, out_file=out_file)

    def check_exists(self, repo_name: str) -> bool:
        """Check if the repo exists in the project."""
        output = StringIO()
        return not self._invoke(['repos',
                                 'show',
                                 '--organization',
                                 self._config.organisation_url,
                                 '--project',
                                 self._config.project,
                                 '-r',
                                 repo_name],
                                out_file=output)

    def create(self, repo_name: str):
        """Create the repo in the project."""
        output = StringIO()
        return self._invoke(['repos',
                             'create',
                             '--organization',
                             self._config.organisation_url,
                             '--project',
                             self._config.project,
                             '--name',
                             repo_name],
                            out_file=output)

    def delete(self, repo_name: str):
        """Delete the repo if it exists in the project."""
        # We need to get the ID
        show_output = StringIO()
        result = self._invoke(['repos',
                               'show',
                               '--organization',
                               self._config.organisation_url,
                               '--project',
                               self._config.project,
                               '-r',
                               repo_name],
                              out_file=show_output)
        if not result:
            # Exists
            repo_info = json.loads(show_output.getvalue())
            repo_id = repo_info['id']
            output = StringIO()
            return self._invoke(['repos',
                                 'delete',
                                 '--organization',
                                 self._config.organisation_url,
                                 '--project',
                                 self._config.project,
                                 '--id',
                                 repo_id],
                                out_file=output)

    def get_remote_url(self, repo_name: str) -> HttpUrl:
        """Get the remote url for the repo."""
        output = StringIO()
        result = self._invoke(['repos',
                               'show',
                               '--organization',
                               self._config.organisation_url,
                               '--project',
                               self._config.project,
                               '-r',
                               repo_name],
                              out_file=output)
        if not result:
            # Exists
            repo_info = json.loads(output.getvalue())
            return repo_info['remoteUrl']

    def list(self) -> List[str]:
        """List the repos in the project."""
        output = StringIO()
        result = self._invoke(['repos',
                               'list',
                               '--organization',
                               self._config.organisation_url,
                               '--project',
                               self._config.project],
                              out_file=output)
        if not result:
            # Exists
            repo_list = [u['name'] for u in json.loads(output.getvalue())]
            return repo_list
