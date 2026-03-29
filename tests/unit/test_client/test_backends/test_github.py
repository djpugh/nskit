"""Unit tests for GitHubBackend."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from nskit.client.backends.github import GitHubBackend


class TestGitHubBackendRepoName(unittest.TestCase):
    """Tests for GitHubBackend._get_repo_name."""

    def test_default_pattern(self) -> None:
        """Default pattern uses recipe name as repo name."""
        backend = GitHubBackend(org="myorg", token="fake")
        self.assertEqual(backend._get_repo_name("my-recipe"), "my-recipe")

    def test_custom_pattern(self) -> None:
        """Custom pattern interpolates recipe name."""
        backend = GitHubBackend(
            org="myorg",
            repo_pattern="recipe-{recipe_name}",
            token="fake",
        )
        self.assertEqual(
            backend._get_repo_name("auth"),
            "recipe-auth",
        )


class TestGitHubBackendGetImageUrl(unittest.TestCase):
    """Tests for GitHubBackend.get_image_url."""

    def test_image_url_format(self) -> None:
        """Image URL follows ghcr.io/org/repo:version format."""
        backend = GitHubBackend(org="myorg", token="fake")
        url = backend.get_image_url("recipe", "1.0.0")
        self.assertEqual(url, "ghcr.io/myorg/recipe:1.0.0")


class TestGitHubBackendEntrypoint(unittest.TestCase):
    """Tests for GitHubBackend.entrypoint property."""

    def test_default_entrypoint(self) -> None:
        """Default entrypoint is 'nskit.recipes'."""
        backend = GitHubBackend(org="org", token="t")
        self.assertEqual(backend.entrypoint, "nskit.recipes")

    def test_custom_entrypoint(self) -> None:
        """Custom entrypoint is returned."""
        backend = GitHubBackend(org="org", token="t", entrypoint="custom")
        self.assertEqual(backend.entrypoint, "custom")


class TestGitHubBackendGetToken(unittest.TestCase):
    """Tests for GitHubBackend._get_token."""

    def test_returns_provided_token(self) -> None:
        """Returns the token passed at init."""
        backend = GitHubBackend(org="org", token="my-token")
        self.assertEqual(backend._get_token(), "my-token")

    @patch("nskit.client.backends.github.subprocess")
    def test_falls_back_to_gh_cli(
        self,
        mock_subprocess: MagicMock,
    ) -> None:
        """Falls back to gh CLI when no token provided."""
        mock_result = MagicMock()
        mock_result.stdout = "gh-cli-token\n"
        mock_subprocess.run.return_value = mock_result
        mock_subprocess.CalledProcessError = Exception

        backend = GitHubBackend(org="org")
        token = backend._get_token()
        self.assertEqual(token, "gh-cli-token")

    @patch("nskit.client.backends.github.subprocess")
    def test_raises_when_gh_cli_missing(
        self,
        mock_subprocess: MagicMock,
    ) -> None:
        """Raises RuntimeError when gh CLI is not installed."""
        mock_subprocess.run.side_effect = FileNotFoundError
        backend = GitHubBackend(org="org")
        with self.assertRaises(RuntimeError):
            backend._get_token()


class TestGitHubBackendGetRecipeVersions(unittest.TestCase):
    """Tests for GitHubBackend.get_recipe_versions."""

    def test_returns_release_tags(self) -> None:
        """Returns tag names from non-draft releases."""
        backend = GitHubBackend(org="org", token="t")

        mock_release_1 = MagicMock()
        mock_release_1.tag_name = "1.0.0"
        mock_release_1.draft = False
        mock_release_2 = MagicMock()
        mock_release_2.tag_name = "2.0.0"
        mock_release_2.draft = False
        mock_draft = MagicMock()
        mock_draft.tag_name = "3.0.0-rc1"
        mock_draft.draft = True

        mock_client = MagicMock()
        mock_client.repos.list_releases.return_value = [
            mock_release_1,
            mock_release_2,
            mock_draft,
        ]
        backend._github = mock_client

        versions = backend.get_recipe_versions("recipe")
        self.assertEqual(versions, ["1.0.0", "2.0.0"])

    def test_returns_empty_on_error(self) -> None:
        """Returns empty list when API call fails."""
        backend = GitHubBackend(org="org", token="t")
        mock_client = MagicMock()
        mock_client.repos.list_releases.side_effect = Exception("API error")
        backend._github = mock_client

        versions = backend.get_recipe_versions("recipe")
        self.assertEqual(versions, [])


if __name__ == "__main__":
    unittest.main()
