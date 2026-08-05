"""Abstract classes for the provider."""

from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Optional

from pydantic import HttpUrl

from nskit.common.configuration import BaseConfiguration


class RepoClient(ABC):
    """Repo management client."""

    @abstractmethod
    def create(self, repo_name: str):
        """Create a repo."""
        raise NotImplementedError()

    @abstractmethod
    def get_remote_url(self, repo_name: str) -> HttpUrl:
        """Get the remote url for a repo."""
        raise NotImplementedError()

    def get_clone_url(self, repo_name: str) -> HttpUrl:
        """Get the clone URL.

        This defaults to the remote url unless specifically implemented.
        """
        return self.get_remote_url(repo_name)

    @abstractmethod
    def delete(self, repo_name: str):
        """Delete a repo."""
        raise NotImplementedError()

    @abstractmethod
    def check_exists(self, repo_name: str) -> bool:
        """Check if the repo exists on the remote."""
        raise NotImplementedError()

    @abstractmethod
    def list(self) -> list[str]:
        """List all repos on the remote."""
        raise NotImplementedError()

    def configure(self, repo_name: str, settings: Optional[dict[str, Any]] = None) -> None:
        """Apply repository-level configuration (e.g. merge options, features).

        Default is a no-op so providers that do not support remote configuration
        remain valid. Providers should override to apply ``settings`` to the repo.
        """
        return None

    def set_branch_protection(
        self,
        repo_name: str,
        branch: str,
        rules: Optional[dict[str, Any]] = None,
    ) -> None:
        """Apply classic branch protection configuration to ``branch``.

        Default is a no-op so providers without branch-protection support remain
        valid. Providers should override to apply ``rules`` to the named branch.

        Prefer the ruleset methods below where the provider supports them;
        rulesets are the successor to classic branch protection.
        """
        return None

    def create_ruleset(self, repo_name: str, ruleset: Any) -> Optional[int]:
        """Create a ruleset on the repo, returning its ID if the provider gives one.

        Default is a no-op so providers without ruleset support remain valid.
        """
        return None

    # NB: the return annotation is quoted because ``list`` is also a method on
    # this class, so an unquoted ``list[Any]`` would resolve to that method.
    def list_rulesets(self, repo_name: str) -> "list[Any]":
        """List the repo's rulesets. Default is an empty list."""
        return []

    def update_ruleset(self, repo_name: str, ruleset_id: int, **changes: Any) -> None:
        """Update fields on an existing ruleset. Default is a no-op."""
        return None

    def delete_ruleset(self, repo_name: str, ruleset_id: int) -> None:
        """Delete a ruleset. Default is a no-op."""
        return None


class VCSProviderSettings(ABC, BaseConfiguration):
    """Settings for VCS Provider."""

    @abstractproperty
    def repo_client(self) -> RepoClient:
        """Return the instantiated repo client object for the provider."""
        raise NotImplementedError()
