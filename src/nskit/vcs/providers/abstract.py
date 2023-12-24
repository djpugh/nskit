"""Abstract classes for the provider."""
from abc import ABC, abstractmethod, abstractproperty
from typing import List

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
    def list(self) -> List[str]:
        """List all repos on the remote."""
        raise NotImplementedError()


class VCSProviderSettings(ABC, BaseConfiguration):
    """Settings for VCS Provider."""

    @abstractproperty
    def repo_client(self) -> RepoClient:
        """Return the instantiated repo client object for the provider."""
        raise NotImplementedError()
