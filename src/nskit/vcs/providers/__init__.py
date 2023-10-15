"""VCS Providers, accessed using entrypoints."""
from nskit.common.extensions import ExtensionsEnum
from nskit.vcs.providers._base import RepoClient, VCSProviderSettings  # noqa: F401


ProviderEnum = ExtensionsEnum.from_entrypoint('ProviderEnum', 'nskit.vcs.providers')
