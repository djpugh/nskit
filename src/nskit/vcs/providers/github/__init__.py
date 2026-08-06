"""GitHub VCS provider.

The provider implementation lives in :mod:`~nskit.vcs.providers.github.provider`
and the composable ruleset models in :mod:`~nskit.vcs.providers.github.rulesets`.
Rulesets are a GitHub-specific concept, so they belong under this package rather
than alongside the provider-agnostic abstractions in ``nskit.vcs.providers``.

The provider's public names are re-exported here so
``nskit.vcs.providers.github:GithubSettings`` keeps working as the entry point.
"""

from nskit.vcs.providers.github.provider import (
    GithubBranchProtectionSettings,
    GithubOrgType,
    GithubRepoClient,
    GithubRepoSettings,
    GithubSettings,
    gh_cli_token,
)

__all__ = [
    "GithubBranchProtectionSettings",
    "GithubOrgType",
    "GithubRepoClient",
    "GithubRepoSettings",
    "GithubSettings",
    "gh_cli_token",
]
