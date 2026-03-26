"""Repository client for managing recipe repositories."""

from __future__ import annotations

from nskit.client.models import RepositoryInfo
from nskit.vcs.providers.abstract import RepoClient


class RepositoryClient:
    """Client for managing recipe repositories."""

    def __init__(self, vcs_client: RepoClient | None = None):
        """Initialize repository client.

        Args:
            vcs_client: Optional VCS client (e.g., GithubRepoClient)
        """
        self.vcs_client = vcs_client

    def create_repository(
        self,
        repo_name: str,
        description: str | None = None,
        private: bool = True,
    ) -> RepositoryInfo:
        """Create a new repository.

        Args:
            repo_name: Repository name
            description: Repository description
            private: Whether repository is private

        Returns:
            Repository info
        """
        if not self.vcs_client:
            raise ValueError("VCS client not configured")

        self.vcs_client.create(repo_name)

        return RepositoryInfo(
            name=repo_name,
            url=f"https://github.com/{repo_name}",  # Simplified
            description=description,
        )

    def configure_repository(
        self,
        repo_name: str,
        branch_protection: bool = True,
        require_reviews: bool = True,
    ) -> None:
        """Configure repository settings.

        Args:
            repo_name: Repository name
            branch_protection: Enable branch protection
            require_reviews: Require pull request reviews
        """
        if not self.vcs_client:
            raise ValueError("VCS client not configured")

        # Repository configuration would go here
        # This is a placeholder for future implementation
        pass

    def get_repository_info(self, repo_name: str) -> RepositoryInfo | None:
        """Get repository information.

        Args:
            repo_name: Repository name

        Returns:
            Repository info or None if not found
        """
        if not self.vcs_client:
            return None

        # This would fetch actual repo info
        # Placeholder for now
        return RepositoryInfo(
            name=repo_name,
            url=f"https://github.com/{repo_name}",
        )
