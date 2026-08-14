"""Unit tests for UpdateClient with mocked backends."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from nskit.client.exceptions import GitStatusError
from nskit.client.update import UpdateClient


class TestUpdateClient(unittest.TestCase):
    """Test UpdateClient functionality."""

    def setUp(self):
        """Set up mock backend and mock project."""
        self.mock_backend = Mock()
        self.mock_backend.entrypoint = "test.recipes"
        self.mock_backend.get_recipe_versions.return_value = ["v1.0.0", "v1.1.0", "v2.0.0"]
        self.mock_backend.fetch_recipe.return_value = Path("/tmp/recipe")

        self._tmp_dir = TemporaryDirectory()
        tmp_path = Path(self._tmp_dir.name)

        self.mock_project = tmp_path / "project"
        self.mock_project.mkdir()

        recipe_dir = self.mock_project / ".recipe"
        recipe_dir.mkdir()

        config_file = recipe_dir / "config.yml"
        config_file.write_text("metadata:\n  recipe_name: python_package\n  docker_image: test/python_package:v1.0.0\n")

    def tearDown(self):
        """Clean up temporary directory."""
        self._tmp_dir.cleanup()

    def test_check_update_available_no_config(self):
        """Test checking for updates with no recipe config."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            client = UpdateClient(self.mock_backend)
            latest = client.check_update_available(tmp_path)
            self.assertIsNone(latest)

    def test_check_update_available_no_update(self):
        """Test checking for updates when already on latest."""
        self.mock_backend.get_recipe_versions.return_value = ["v1.0.0"]
        client = UpdateClient(self.mock_backend)
        latest = client.check_update_available(self.mock_project)
        self.assertIsNone(latest)

    @patch("nskit.client.update.GitUtils")
    def test_update_project_not_git_repo(self, mock_git_cls):
        """Test update raises GitStatusError if not a git repository."""
        mock_git_cls.return_value.is_git_repository.return_value = False

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            client = UpdateClient(self.mock_backend)
            with self.assertRaisesRegex(GitStatusError, "not a git repository"):
                client.update_project(project_path=tmp_path, target_version="v2.0.0")

    @patch("nskit.client.update.GitUtils")
    def test_update_project_uncommitted_changes(self, mock_git_cls):
        """Test update raises GitStatusError with uncommitted changes."""
        mock_git_cls.return_value.is_git_repository.return_value = True
        mock_git_cls.return_value.has_uncommitted_changes.return_value = True

        client = UpdateClient(self.mock_backend)
        with self.assertRaisesRegex(GitStatusError, "uncommitted changes"):
            client.update_project(project_path=self.mock_project, target_version="v2.0.0")

    @patch("nskit.client.update.GitUtils")
    def test_update_project_dry_run_no_file_changes(self, mock_git_cls):
        """Test dry run doesn't modify files."""
        mock_git_cls.return_value.is_git_repository.return_value = True
        mock_git_cls.return_value.has_uncommitted_changes.return_value = False

        test_file = self.mock_project / "test.py"
        test_file.write_text("original content")

        client = UpdateClient(self.mock_backend)
        try:
            client.update_project(
                project_path=self.mock_project,
                target_version="v2.0.0",
                dry_run=True,
            )
        except Exception:
            pass

        self.assertEqual(test_file.read_text(), "original content")


if __name__ == "__main__":
    unittest.main()
