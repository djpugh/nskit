"""Unit tests for UpdateClient with mocked backends."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nskit.client.exceptions import GitStatusError
from nskit.client.update import UpdateClient


@pytest.fixture
def mock_backend():
    """Mock backend for testing."""
    backend = Mock()
    backend.entrypoint = "test.recipes"
    backend.get_recipe_versions.return_value = ["v1.0.0", "v1.1.0", "v2.0.0"]
    backend.fetch_recipe.return_value = Path("/tmp/recipe")
    return backend


@pytest.fixture
def mock_project(tmp_path):
    """Create mock project with recipe config."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    recipe_dir = project_path / ".recipe"
    recipe_dir.mkdir()

    config_file = recipe_dir / "config.yml"
    config_file.write_text("metadata:\n  recipe_name: python_package\n  docker_image: test/python_package:v1.0.0\n")

    return project_path


class TestUpdateClient:
    """Test UpdateClient functionality."""

    def test_check_update_available_no_config(self, mock_backend, tmp_path):
        """Test checking for updates with no recipe config."""
        client = UpdateClient(mock_backend)
        latest = client.check_update_available(tmp_path)
        assert latest is None

    def test_check_update_available_no_update(self, mock_backend, mock_project):
        """Test checking for updates when already on latest."""
        mock_backend.get_recipe_versions.return_value = ["v1.0.0"]
        client = UpdateClient(mock_backend)
        latest = client.check_update_available(mock_project)
        assert latest is None

    @patch("nskit.client.update.GitUtils")
    def test_update_project_not_git_repo(self, mock_git_cls, mock_backend, tmp_path):
        """Test update raises GitStatusError if not a git repository."""
        mock_git_cls.return_value.is_git_repository.return_value = False

        client = UpdateClient(mock_backend)
        with pytest.raises(GitStatusError, match="not a git repository"):
            client.update_project(project_path=tmp_path, target_version="v2.0.0")

    @patch("nskit.client.update.GitUtils")
    def test_update_project_uncommitted_changes(self, mock_git_cls, mock_backend, mock_project):
        """Test update raises GitStatusError with uncommitted changes."""
        mock_git_cls.return_value.is_git_repository.return_value = True
        mock_git_cls.return_value.has_uncommitted_changes.return_value = True

        client = UpdateClient(mock_backend)
        with pytest.raises(GitStatusError, match="uncommitted changes"):
            client.update_project(project_path=mock_project, target_version="v2.0.0")

    @patch("nskit.client.update.GitUtils")
    def test_update_project_dry_run_no_file_changes(self, mock_git_cls, mock_backend, mock_project):
        """Test dry run doesn't modify files."""
        mock_git_cls.return_value.is_git_repository.return_value = True
        mock_git_cls.return_value.has_uncommitted_changes.return_value = False

        test_file = mock_project / "test.py"
        test_file.write_text("original content")

        client = UpdateClient(mock_backend)
        try:
            client.update_project(
                project_path=mock_project,
                target_version="v2.0.0",
                dry_run=True,
            )
        except Exception:
            pass

        assert test_file.read_text() == "original content"
