"""Repository client for managing recipe repositories."""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path

from nskit.client.models import RepositoryInfo
from nskit.vcs.providers.abstract import RepoClient


class RepositoryClient:
    """Client for managing recipe repositories."""

    def __init__(self, vcs_client: RepoClient | None = None):
        """Initialise repository client.

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
        """Create a new remote repository.

        Args:
            repo_name: Repository name.
            description: Repository description.
            private: Whether repository is private.

        Returns:
            Repository info including the remote URL.
        """
        if not self.vcs_client:
            raise ValueError("VCS client not configured")

        self.vcs_client.create(repo_name)
        url = str(self.vcs_client.get_remote_url(repo_name))

        return RepositoryInfo(
            name=repo_name,
            url=url,
            description=description,
        )

    def create_and_push(
        self,
        repo_name: str,
        project_path: Path,
        description: str | None = None,
        private: bool = True,
    ) -> RepositoryInfo:
        """Create a remote repository and push an existing local repo to it.

        Expects the project to already have a git repo with at least
        one commit.

        Args:
            repo_name: Repository name.
            project_path: Local project directory to push.
            description: Repository description.
            private: Whether repository is private.

        Returns:
            Repository info including the remote URL.
        """
        info = self.create_repository(repo_name, description=description, private=private)
        clone_url = str(self.vcs_client.get_clone_url(repo_name))

        subprocess.run(  # nosec B603, B607
            ["git", "remote", "add", "origin", clone_url],
            cwd=project_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(  # nosec B603, B607
            ["git", "push", "-u", "origin", "HEAD"],
            cwd=project_path,
            capture_output=True,
            check=True,
        )

        return info

    def configure_repository(
        self,
        repo_name: str,
        branch_protection: bool = True,
        require_reviews: bool = True,
    ) -> None:
        """Configure repository settings.

        Not yet implemented — placeholder for future configuration logic.

        Args:
            repo_name: Repository name.
            branch_protection: Enable branch protection.
            require_reviews: Require pull request reviews.
        """
        if not self.vcs_client:
            raise ValueError("VCS client not configured")

    def get_repository_info(self, repo_name: str) -> RepositoryInfo | None:
        """Get repository information.

        Args:
            repo_name: Repository name.

        Returns:
            Repository info or ``None`` if not found.
        """
        if not self.vcs_client:
            return None

        url = str(self.vcs_client.get_remote_url(repo_name))
        return RepositoryInfo(name=repo_name, url=url)
