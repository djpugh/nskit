"""Functional tests for UpdateClient with mocked backends."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nskit.client.models import UpdateResult
from nskit.mixer.update import DiffMode, MergeResult
from nskit.recipes import UpdateClient


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

    # Create .recipe/config.yml
    recipe_dir = project_path / ".recipe"
    recipe_dir.mkdir()

    # Create config with version
    config_file = recipe_dir / "config.yml"
    config_file.write_text(
        """metadata:
  recipe_name: v1.0.0
  recipe_version: v1.0.0
"""
    )

    return project_path

    config_content = """
metadata:
  recipe_name: python_package
  recipe_version: v1.0.0
  docker_image: test/python_package:v1.0.0
  github_repo: test/python_package
"""
    (recipe_dir / "config.yml").write_text(config_content)

    # Initialize git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_path, capture_output=True)

    return project_path


class TestUpdateClient:
    """Test UpdateClient functionality."""

    def test_check_update_available_newer_version(self, mock_backend, mock_project):
        """Test checking for updates when newer version exists."""
        # Mock the config loading to avoid file system issues
        with patch("nskit.mixer.components.RecipeConfig") as mock_config_class:
            mock_config = Mock()
            mock_config.metadata = Mock()
            mock_config.metadata.recipe_name = "v1.0.0"
            mock_config_class.load_from_file.return_value = mock_config

            client = UpdateClient(mock_backend)
            latest = client.check_update_available(mock_project)

            assert latest == "v2.0.0"

    def test_check_update_available_no_update(self, mock_backend, mock_project):
        """Test checking for updates when already on latest."""
        mock_backend.get_recipe_versions.return_value = ["v1.0.0"]
        client = UpdateClient(mock_backend)

        latest = client.check_update_available(mock_project)

        assert latest is None

    def test_check_update_available_no_config(self, mock_backend, tmp_path):
        """Test checking for updates with no recipe config."""
        client = UpdateClient(mock_backend)

        latest = client.check_update_available(tmp_path)

        assert latest is None

    @patch("nskit.client.update.GitUtils")
    def test_update_project_not_git_repo(self, mock_git_utils, mock_backend, tmp_path):
        """Test update fails if not a git repository."""
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = False
        mock_git_utils.return_value = mock_git_instance

        client = UpdateClient(mock_backend)
        result = client.update_project(
            project_path=tmp_path,
            target_version="v2.0.0",
        )

        assert not result.success
        assert "not a git repository" in result.errors[0]

    @patch("nskit.client.update.GitUtils")
    def test_update_project_uncommitted_changes(self, mock_git_utils, mock_backend, mock_project):
        """Test update fails with uncommitted changes."""
        mock_git_instance = Mock()
        mock_git_instance.is_git_repository.return_value = True
        mock_git_instance.has_uncommitted_changes.return_value = True
        mock_git_utils.return_value = mock_git_instance

        client = UpdateClient(mock_backend)
        result = client.update_project(
            project_path=mock_project,
            target_version="v2.0.0",
        )

        assert not result.success
        assert "uncommitted changes" in result.errors[0]

    def test_update_project_dry_run(self, mock_backend, mock_project):
        """Test dry run doesn't modify files."""
        client = UpdateClient(mock_backend)

        # Create a test file
        test_file = mock_project / "test.py"
        test_file.write_text("original content")
        original_content = test_file.read_text()

        client.update_project(
            project_path=mock_project,
            target_version="v2.0.0",
            dry_run=True,
        )

        # File should not be modified
        assert test_file.read_text() == original_content
