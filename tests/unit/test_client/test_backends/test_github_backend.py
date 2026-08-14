"""Tests for GitHub backend with mocked API."""

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from nskit.client.backends import GitHubBackend
from nskit.client.models import RecipeInfo


class TestGitHubBackend(unittest.TestCase):
    """Test GitHubBackend with mocked GitHub API."""

    def setUp(self):
        """Set up patchers for ghapi and subprocess."""
        self.ghapi_patcher = patch("nskit.client.backends.github.sync_ghapi")
        self.subprocess_patcher = patch("nskit.client.backends.github.subprocess")

        self.mock_ghapi = self.ghapi_patcher.start()
        self.mock_subprocess = self.subprocess_patcher.start()
        self.mock_subprocess.run.return_value = Mock(stdout="test_token\n")

    def tearDown(self):
        """Stop patchers."""
        self.ghapi_patcher.stop()
        self.subprocess_patcher.stop()

    def test_initialization(self):
        """Test backend initialization."""
        backend = GitHubBackend(org="testorg", token="test_token")

        self.assertEqual(backend.org, "testorg")
        self.assertEqual(backend._token.get_secret_value(), "test_token")

    def test_get_token_from_gh_cli(self):
        """Test getting token from gh CLI."""
        backend = GitHubBackend(org="testorg")
        token = backend._get_token()

        self.assertEqual(token, "test_token")
        self.mock_subprocess.run.assert_called_once()

    def test_list_recipes(self):
        """Test listing recipes from GitHub."""
        # Mock GitHub API responses
        mock_client = MagicMock()
        self.mock_ghapi.return_value = mock_client

        # Mock repos
        mock_repo1 = Mock()
        mock_repo1.name = "recipe-python"
        mock_repo1.description = "Python recipe"

        mock_repo2 = Mock()
        mock_repo2.name = "recipe-typescript"
        mock_repo2.description = "TypeScript recipe"

        mock_client.repos.list_for_org.return_value = [mock_repo1, mock_repo2]

        # Mock releases
        mock_release1 = Mock()
        mock_release1.tag_name = "v1.0.0"
        mock_release1.draft = False

        mock_release2 = Mock()
        mock_release2.tag_name = "v1.1.0"
        mock_release2.draft = False

        mock_client.repos.list_releases.return_value = [mock_release1, mock_release2]

        # Test
        backend = GitHubBackend(org="testorg", token="test_token")
        recipes = backend.list_recipes()

        self.assertEqual(len(recipes), 2)
        self.assertEqual(recipes[0].name, "recipe-python")
        self.assertEqual(recipes[0].description, "Python recipe")
        self.assertEqual(len(recipes[0].versions), 2)

    def test_get_recipe_versions(self):
        """Test getting recipe versions."""
        mock_client = MagicMock()
        self.mock_ghapi.return_value = mock_client

        # Mock releases
        mock_release1 = Mock()
        mock_release1.tag_name = "v1.0.0"
        mock_release1.draft = False

        mock_release2 = Mock()
        mock_release2.tag_name = "v2.0.0"
        mock_release2.draft = False

        mock_release3 = Mock()
        mock_release3.tag_name = "v3.0.0"
        mock_release3.draft = True  # Should be excluded

        mock_client.repos.list_releases.return_value = [mock_release1, mock_release2, mock_release3]

        backend = GitHubBackend(org="testorg", token="test_token")
        versions = backend.get_recipe_versions("python_package")

        self.assertEqual(len(versions), 2)
        self.assertIn("v1.0.0", versions)
        self.assertIn("v2.0.0", versions)
        self.assertNotIn("v3.0.0", versions)  # Draft excluded

    def test_fetch_recipe(self):
        """Test fetching recipe from GitHub."""
        mock_client = MagicMock()
        self.mock_ghapi.return_value = mock_client

        # Mock release
        mock_release = Mock()
        mock_release.tag_name = "v1.0.0"
        mock_client.repos.get_release_by_tag.return_value = mock_release

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with patch("nskit.client.backends.github.subprocess") as mock_sub:
                mock_sub.run.return_value = Mock(returncode=0)

                with patch("nskit.client.backends.github.zipfile.ZipFile") as mock_zip:
                    mock_zip_instance = MagicMock()
                    mock_zip.return_value.__enter__.return_value = mock_zip_instance

                    backend = GitHubBackend(org="testorg", token="test_token")
                    result = backend.fetch_recipe("python_package", "v1.0.0", tmp_path)

                    self.assertIsNotNone(result)
                    mock_client.repos.get_release_by_tag.assert_called_once()

    def test_repo_pattern_substitution(self):
        """Test repository pattern substitution."""
        backend = GitHubBackend(org="testorg", repo_pattern="recipe-{recipe_name}", token="test_token")

        repo_name = backend._get_repo_name("python_package")
        self.assertEqual(repo_name, "recipe-python_package")

    def test_list_recipes_handles_api_errors(self):
        """Test list_recipes handles API errors gracefully."""
        mock_client = MagicMock()
        self.mock_ghapi.return_value = mock_client

        mock_repo = Mock()
        mock_repo.name = "recipe-python"
        mock_repo.description = "Python recipe"

        mock_client.repos.list_for_org.return_value = [mock_repo]
        mock_client.repos.list_releases.side_effect = Exception("API Error")

        backend = GitHubBackend(org="testorg", token="test_token")
        recipes = backend.list_recipes()

        # Should handle error gracefully and return repo without versions
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].name, "recipe-python")

    def test_get_token_not_logged_in(self):
        """Test error when gh CLI not authenticated."""
        # Stop the default subprocess patcher for this test
        self.subprocess_patcher.stop()

        with patch("nskit.client.backends.github.subprocess") as mock_sub:
            mock_sub.CalledProcessError = subprocess.CalledProcessError
            mock_sub.run.side_effect = subprocess.CalledProcessError(1, "gh")

            backend = GitHubBackend(org="testorg")

            with self.assertRaisesRegex(RuntimeError, "gh auth login"):
                backend._get_token()

        # Restart the patcher for tearDown
        self.mock_subprocess = self.subprocess_patcher.start()

    def test_get_token_gh_not_installed(self):
        """Test error when gh CLI not installed."""
        # Stop the default subprocess patcher for this test
        self.subprocess_patcher.stop()

        with patch("nskit.client.backends.github.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            backend = GitHubBackend(org="testorg")

            with self.assertRaisesRegex(RuntimeError, "install it"):
                backend._get_token()

        # Restart the patcher for tearDown
        self.mock_subprocess = self.subprocess_patcher.start()


if __name__ == "__main__":
    unittest.main()
