"""Tests for RepositoryClient."""

import subprocess
import unittest
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch


class TestRepositoryClient(unittest.TestCase):
    """Tests for RepositoryClient."""

    def test_create_repository(self) -> None:
        """Creates a repository via the VCS client."""
        from nskit.recipes.repository_client import RepositoryClient

        vcs = MagicMock()
        vcs.get_remote_url.return_value = "https://github.com/org/my-repo"
        client = RepositoryClient(vcs_client=vcs)
        result = client.create_repository("my-repo", description="A repo")

        vcs.create.assert_called_once_with("my-repo")
        self.assertEqual(result.name, "my-repo")
        self.assertEqual(result.description, "A repo")
        self.assertIn("github.com", result.url)

    def test_create_repository_no_client_raises(self) -> None:
        """Raises ValueError when no VCS client is configured."""
        from nskit.recipes.repository_client import RepositoryClient

        client = RepositoryClient()
        with self.assertRaises(ValueError):
            client.create_repository("my-repo")

    def test_create_and_push(self) -> None:
        """Creates remote repo, adds origin, and pushes."""
        from nskit.recipes.repository_client import RepositoryClient

        vcs = MagicMock()
        vcs.get_remote_url.return_value = "https://github.com/org/my-repo"
        vcs.get_clone_url.return_value = "https://github.com/org/my-repo.git"

        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=project, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=project, capture_output=True)
            (project / "file.txt").write_text("content")
            subprocess.run(["git", "add", "."], cwd=project, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init", "--no-verify"], cwd=project, capture_output=True, check=True)

            client = RepositoryClient(vcs_client=vcs)
            with patch("nskit.recipes.repository_client.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                info = client.create_and_push("my-repo", project, description="desc")

            vcs.create.assert_called_once_with("my-repo")
            self.assertEqual(info.name, "my-repo")
            # Verify remote add and push were called
            calls = [c.args[0] for c in mock_run.call_args_list]
            self.assertTrue(any("remote" in str(c) for c in calls))
            self.assertTrue(any("push" in str(c) for c in calls))

    def test_configure_repository_no_client_raises(self) -> None:
        """Raises ValueError when no VCS client is configured."""
        from nskit.recipes.repository_client import RepositoryClient

        client = RepositoryClient()
        with self.assertRaises(ValueError):
            client.configure_repository("my-repo")

    def test_configure_repository_with_client(self) -> None:
        """Does not raise when VCS client is configured."""
        from nskit.recipes.repository_client import RepositoryClient

        vcs = MagicMock()
        client = RepositoryClient(vcs_client=vcs)
        client.configure_repository("my-repo")

    def test_get_repository_info_no_client(self) -> None:
        """Returns None when no VCS client is configured."""
        from nskit.recipes.repository_client import RepositoryClient

        client = RepositoryClient()
        self.assertIsNone(client.get_repository_info("my-repo"))

    def test_get_repository_info_with_client(self) -> None:
        """Returns RepositoryInfo when VCS client is configured."""
        from nskit.recipes.repository_client import RepositoryClient

        vcs = MagicMock()
        vcs.get_remote_url.return_value = "https://github.com/org/my-repo"
        client = RepositoryClient(vcs_client=vcs)
        result = client.get_repository_info("my-repo")

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "my-repo")


class TestRecipeClientCreateRepository(unittest.TestCase):
    """Tests for RecipeClient.create_repository."""

    @patch("nskit.client.recipes._detect_repo_client")
    def test_create_repository_no_provider(self, mock_detect) -> None:
        """Returns failure when no VCS provider is detected."""
        mock_detect.return_value = (None, None)

        from nskit.client.recipes import RecipeClient

        backend = MagicMock()
        client = RecipeClient(backend)
        ok, msg = client.create_repository("my-project")

        self.assertFalse(ok)
        self.assertIn("No VCS provider", msg)

    @patch("nskit.client.recipes._detect_repo_client")
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

    @patch("nskit.client.recipes._detect_repo_client")
    def test_create_repository_without_project_path(self, mock_detect) -> None:
        """Creates repo without pushing when no project_path given."""
        mock_vcs = MagicMock()
        mock_vcs.get_remote_url.return_value = "https://github.com/org/my-project"
        mock_detect.return_value = (mock_vcs, "GitHub")

        from nskit.client.recipes import RecipeClient

        backend = MagicMock()
        client = RecipeClient(backend)
        ok, msg = client.create_repository("my-project", description="desc")

        self.assertTrue(ok)
        self.assertIn("Created repository", msg)
        mock_vcs.create.assert_called_once()


class TestDetectRepoClient(unittest.TestCase):
    """Tests for _detect_repo_client."""

    @patch("nskit.vcs.provider_detection.get_default_repo_client")
    def test_returns_client_and_provider(self, mock_get) -> None:
        """Returns (client, provider_name) when detection succeeds."""
        from nskit.client.recipes import _detect_repo_client

        mock_client = MagicMock()
        mock_client.__class__.__name__ = "GithubRepoClient"
        mock_get.return_value = mock_client

        client, name = _detect_repo_client()
        self.assertIs(client, mock_client)
        self.assertEqual(name, "Github")

    @patch("nskit.vcs.provider_detection.get_default_repo_client", side_effect=ValueError("no provider"))
    def test_returns_none_on_failure(self, mock_get) -> None:
        """Returns (None, None) when no provider is configured."""
        from nskit.client.recipes import _detect_repo_client

        client, name = _detect_repo_client()
        self.assertIsNone(client)
        self.assertIsNone(name)
