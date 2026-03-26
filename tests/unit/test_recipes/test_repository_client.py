"""Tests for RepositoryClient."""

import unittest
import unittest.mock
from unittest.mock import MagicMock

from nskit.recipes.repository_client import RepositoryClient


class TestRepositoryClient(unittest.TestCase):
    """Tests for RepositoryClient."""

    def test_create_repository(self) -> None:
        """Creates a repository via the VCS client."""
        vcs = MagicMock()
        client = RepositoryClient(vcs_client=vcs)
        result = client.create_repository("my-repo", description="A repo")

        vcs.create.assert_called_once_with("my-repo")
        self.assertEqual(result.name, "my-repo")
        self.assertEqual(result.description, "A repo")

    def test_create_repository_no_client_raises(self) -> None:
        """Raises ValueError when no VCS client is configured."""
        client = RepositoryClient()
        with self.assertRaises(ValueError):
            client.create_repository("my-repo")

    def test_configure_repository_no_client_raises(self) -> None:
        """Raises ValueError when no VCS client is configured."""
        client = RepositoryClient()
        with self.assertRaises(ValueError):
            client.configure_repository("my-repo")

    def test_configure_repository_with_client(self) -> None:
        """Does not raise when VCS client is configured."""
        vcs = MagicMock()
        client = RepositoryClient(vcs_client=vcs)
        client.configure_repository("my-repo")

    def test_get_repository_info_no_client(self) -> None:
        """Returns None when no VCS client is configured."""
        client = RepositoryClient()
        self.assertIsNone(client.get_repository_info("my-repo"))

    def test_get_repository_info_with_client(self) -> None:
        """Returns RepositoryInfo when VCS client is configured."""
        vcs = MagicMock()
        client = RepositoryClient(vcs_client=vcs)
        result = client.get_repository_info("my-repo")

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "my-repo")


class TestRecipeClientCreateRepository(unittest.TestCase):
    """Tests for RecipeClient.create_repository."""

    @unittest.mock.patch("nskit.client.recipes._detect_repo_client")
    def test_create_repository_success(self, mock_detect) -> None:
        """Creates repo when VCS provider is detected."""
        mock_vcs = MagicMock()
        mock_detect.return_value = (mock_vcs, "GitHub")

        from nskit.client.recipes import RecipeClient

        backend = MagicMock()
        client = RecipeClient(backend)
        ok, msg = client.create_repository("my-project", description="A project")

        self.assertTrue(ok)
        self.assertIn("Created repository", msg)
        mock_vcs.create.assert_called_once_with("my-project")

    @unittest.mock.patch("nskit.client.recipes._detect_repo_client")
    def test_create_repository_no_provider(self, mock_detect) -> None:
        """Returns failure when no VCS provider is detected."""
        mock_detect.return_value = (None, None)

        from nskit.client.recipes import RecipeClient

        backend = MagicMock()
        client = RecipeClient(backend)
        ok, msg = client.create_repository("my-project")

        self.assertFalse(ok)
        self.assertIn("No VCS provider", msg)

    @unittest.mock.patch("nskit.client.recipes._detect_repo_client")
    def test_create_repository_vcs_error(self, mock_detect) -> None:
        """Returns failure when VCS client raises."""
        mock_vcs = MagicMock()
        mock_vcs.create.side_effect = RuntimeError("auth failed")
        mock_detect.return_value = (mock_vcs, "GitHub")

        from nskit.client.recipes import RecipeClient

        backend = MagicMock()
        client = RecipeClient(backend)
        ok, msg = client.create_repository("my-project")

        self.assertFalse(ok)
        self.assertIn("Failed to create repository", msg)


class TestDetectRepoClient(unittest.TestCase):
    """Tests for _detect_repo_client."""

    @unittest.mock.patch("nskit.vcs.provider_detection.get_default_repo_client")
    def test_returns_client_and_provider(self, mock_get) -> None:
        """Returns (client, provider_name) when detection succeeds."""
        from nskit.client.recipes import _detect_repo_client

        mock_client = MagicMock()
        mock_client.__class__.__name__ = "GithubRepoClient"
        mock_get.return_value = mock_client

        client, name = _detect_repo_client()
        self.assertIs(client, mock_client)
        self.assertEqual(name, "Github")

    @unittest.mock.patch("nskit.vcs.provider_detection.get_default_repo_client", side_effect=ValueError("no provider"))
    def test_returns_none_on_failure(self, mock_get) -> None:
        """Returns (None, None) when no provider is configured."""
        from nskit.client.recipes import _detect_repo_client

        client, name = _detect_repo_client()
        self.assertIsNone(client)
        self.assertIsNone(name)
