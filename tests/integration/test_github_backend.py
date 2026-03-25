"""Tests for GitHub backend with mocked API."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from nskit.client.backends import GitHubBackend
from nskit.client.models import RecipeInfo


@pytest.fixture
def mock_ghapi():
    """Mock GhApi client."""
    with patch("nskit.client.backends.github.GhApi") as mock:
        yield mock


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for gh CLI."""
    with patch("nskit.client.backends.github.subprocess") as mock:
        mock.run.return_value = Mock(stdout="test_token\n")
        yield mock


class TestGitHubBackend:
    """Test GitHubBackend with mocked GitHub API."""

    def test_initialization(self, mock_subprocess):
        """Test backend initialization."""
        backend = GitHubBackend(org="testorg", token="test_token")

        assert backend.org == "testorg"
        assert backend._token == "test_token"

    def test_get_token_from_gh_cli(self, mock_subprocess):
        """Test getting token from gh CLI."""
        backend = GitHubBackend(org="testorg")
        token = backend._get_token()

        assert token == "test_token"
        mock_subprocess.run.assert_called_once()

    def test_list_recipes(self, mock_ghapi, mock_subprocess):
        """Test listing recipes from GitHub."""
        # Mock GitHub API responses
        mock_client = MagicMock()
        mock_ghapi.return_value = mock_client

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

        assert len(recipes) == 2
        assert recipes[0].name == "recipe-python"
        assert recipes[0].description == "Python recipe"
        assert len(recipes[0].versions) == 2

    def test_get_recipe_versions(self, mock_ghapi, mock_subprocess):
        """Test getting recipe versions."""
        mock_client = MagicMock()
        mock_ghapi.return_value = mock_client

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

        assert len(versions) == 2
        assert "v1.0.0" in versions
        assert "v2.0.0" in versions
        assert "v3.0.0" not in versions  # Draft excluded

    def test_fetch_recipe(self, mock_ghapi, mock_subprocess, tmp_path):
        """Test fetching recipe from GitHub."""
        mock_client = MagicMock()
        mock_ghapi.return_value = mock_client

        # Mock release
        mock_release = Mock()
        mock_release.tag_name = "v1.0.0"
        mock_client.repos.get_release_by_tag.return_value = mock_release

        with patch("nskit.client.backends.github.subprocess") as mock_sub:
            mock_sub.run.return_value = Mock(returncode=0)

            with patch("nskit.client.backends.github.zipfile.ZipFile") as mock_zip:
                mock_zip_instance = MagicMock()
                mock_zip.return_value.__enter__.return_value = mock_zip_instance

                backend = GitHubBackend(org="testorg", token="test_token")
                result = backend.fetch_recipe("python_package", "v1.0.0", tmp_path)

                assert result is not None
                mock_client.repos.get_release_by_tag.assert_called_once()

    def test_repo_pattern_substitution(self, mock_subprocess):
        """Test repository pattern substitution."""
        backend = GitHubBackend(org="testorg", repo_pattern="recipe-{recipe_name}", token="test_token")

        repo_name = backend._get_repo_name("python_package")
        assert repo_name == "recipe-python_package"

    def test_list_recipes_handles_api_errors(self, mock_ghapi, mock_subprocess):
        """Test list_recipes handles API errors gracefully."""
        mock_client = MagicMock()
        mock_ghapi.return_value = mock_client

        mock_repo = Mock()
        mock_repo.name = "recipe-python"
        mock_repo.description = "Python recipe"

        mock_client.repos.list_for_org.return_value = [mock_repo]
        mock_client.repos.list_releases.side_effect = Exception("API Error")

        backend = GitHubBackend(org="testorg", token="test_token")
        recipes = backend.list_recipes()

        # Should handle error gracefully and return repo without versions
        assert len(recipes) == 1
        assert recipes[0].name == "recipe-python"

    def test_get_token_not_logged_in(self):
        """Test error when gh CLI not authenticated."""
        import subprocess

        with patch("nskit.client.backends.github.subprocess") as mock_sub:
            mock_sub.CalledProcessError = subprocess.CalledProcessError
            mock_sub.run.side_effect = subprocess.CalledProcessError(1, "gh")

            backend = GitHubBackend(org="testorg")

            with pytest.raises(RuntimeError, match="gh auth login"):
                backend._get_token()

    def test_get_token_gh_not_installed(self, mock_ghapi):
        """Test error when gh CLI not installed."""
        with patch("nskit.client.backends.github.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            backend = GitHubBackend(org="testorg")

            with pytest.raises(RuntimeError, match="install it"):
                backend._get_token()
