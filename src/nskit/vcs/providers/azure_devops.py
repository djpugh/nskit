from io import StringIO
import json

from azure.cli.core import get_default_cli
from pydantic_settings import HttpUrl, SettingsConfigDict

from nskit.vcs.providers._base import RepoClient, VCSProviderSettings


# Want to use MS interactive Auth as default, but can't get it working, instead, using cli invoke


class AzureDevOpsSettings(VCSProviderSettings):
    model_config = SettingsConfigDict(env_prefix='AZURE_DEVOPS_', env_file='.env')
    url: HttpUrl = "https://dev.azure.com"
    organisation: str
    project: str

    @property
    def organisation_url(self):
        return f'{self.url}/{self.organisation}'

    @property
    def project_url(self):
        return f'{self.organisation_url}/{self.project}'

    @property
    def repo_client(self) -> 'AzureDevOpsRepoClient':
        return AzureDevOpsRepoClient(self)


class AzureDevOpsRepoClient(RepoClient):

    def __init__(self, config: AzureDevOpsSettings):
        self._cli = get_default_cli()
        self._config = config

    def _invoke(self, command, out_file=None):
        return self._cli.invoke(command, out_file=out_file)

    def check_exists(self, name):
        output = StringIO()
        return not self._invoke(['repos',
                                 'show',
                                 '--organization',
                                 self._config.organisation_url,
                                 '--project',
                                 self._config.project,
                                 '-r',
                                 name],
                                out_file=output)

    def create(self, name):
        output = StringIO()
        return self._invoke(['repos',
                             'create',
                             '--organization',
                             self._config.organisation_url,
                             '--project',
                             self._config.project,
                             '--name',
                             name],
                            out_file=output)

    def delete(self, name):
        # We need to get the ID
        show_output = StringIO()
        result = self._invoke(['repos',
                               'show',
                               '--organization',
                               self._config.organisation_url,
                               '--project',
                               self._config.project,
                               '-r',
                               name],
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

    def get_remote_url(self, name):
        output = StringIO()
        result = self._invoke(['repos',
                               'show',
                               '--organization',
                               self._config.organisation_url,
                               '--project',
                               self._config.project,
                               '-r',
                               name],
                              out_file=output)
        if not result:
            # Exists
            repo_info = json.loads(output.getvalue())
            return repo_info['remoteUrl']

    def list(self):
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
