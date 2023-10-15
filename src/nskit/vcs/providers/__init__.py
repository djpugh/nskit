"""VCS Providers, accessed using entrypoints."""
from nskit.common.extensions import ExtensionsEnum
from nskit.vcs.providers.abstract import RepoClient, VCSProviderSettings  # noqa: F401

ENTRYPOINT = 'nskit.vcs.providers'
ProviderEnum = ExtensionsEnum.from_entrypoint('ProviderEnum', ENTRYPOINT)
