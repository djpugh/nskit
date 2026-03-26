"""End-to-end integration tests for complete user workflows."""

import subprocess
from pathlib import Path

import pytest

from nskit.client.backends import LocalBackend
from nskit.mixer.update import DiffMode
from nskit.recipes import RecipeClient, UpdateClient


@pytest.fixture
def recipe_backend(tmp_path):
    """Create a backend with real recipe files."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # Create v1.0.0
    v1 = recipes_dir / "test_recipe" / "v1.0.0"
    v1.mkdir(parents=True)
    (v1 / "README.md").write_text("# {{project_name}}\n\nVersion 1.0.0")
    (v1 / "config.txt").write_text("setting=value1")

    # Create v2.0.0
    v2 = recipes_dir / "test_recipe" / "v2.0.0"
    v2.mkdir(parents=True)
    (v2 / "README.md").write_text("# {{project_name}}\n\nVersion 2.0.0\n\nNew features!")
    (v2 / "config.txt").write_text("setting=value2\nnew_setting=enabled")
    (v2 / "CHANGELOG.md").write_text("## v2.0.0\n- Added features")

    return LocalBackend(recipes_dir=recipes_dir)


class TestEndToEndWorkflows:
    """Test complete user workflows end-to-end."""

    def test_initialize_recipe_fails_on_non_empty_dir(self, recipe_backend, tmp_path):
        """Test initialization fails on non-empty directory."""
        client = RecipeClient(recipe_backend)
        output_dir = tmp_path / "existing"
        output_dir.mkdir()
        (output_dir / "existing.txt").write_text("existing")

        result = client.initialize_recipe(
            recipe="test_recipe", version="v1.0.0", parameters={"project_name": "test"}, output_dir=output_dir
        )

        assert not result.success
        assert "not empty" in result.errors[0].lower()

    def test_update_project_three_way_merge(self, recipe_backend, tmp_path):
        """Test updating project with 3-way merge preserves user changes."""
        # Initialize project with v1.0.0
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Setup git
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, capture_output=True)

        # Create initial files (simulating v1.0.0)
        (project_dir / "README.md").write_text("# my_project\n\nVersion 1.0.0")
        (project_dir / "config.txt").write_text("setting=value1")

        # Create recipe config
        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
              recipe_name: test_recipe
              docker_image: test/test_recipe:v1.0.0
            """
        )

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_dir, capture_output=True, check=True)

        # User makes changes
        readme = project_dir / "README.md"
        readme.write_text("# my_project\n\nVersion 1.0.0\n\nUser added content")

        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "User changes"], cwd=project_dir, capture_output=True, check=True)

        # Update to v2.0.0
        client = UpdateClient(recipe_backend)
        result = client.update_project(
            project_path=project_dir, target_version="v2.0.0", diff_mode=DiffMode.THREE_WAY, dry_run=False
        )

        assert result.success or len(result.errors) == 0

        # Verify user content preserved
        readme_content = readme.read_text()
        assert "User added content" in readme_content or "Version 2.0.0" in readme_content

        # Verify new files added
        assert (project_dir / "CHANGELOG.md").exists()

    def test_update_project_detects_conflicts(self, recipe_backend, tmp_path):
        """Test update detects conflicts when user and recipe modify same lines."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Setup git
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, capture_output=True)

        # Create initial files
        config_file = project_dir / "config.txt"
        config_file.write_text("setting=value1")

        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
              recipe_name: test_recipe
              docker_image: test/test_recipe:v1.0.0
            """
        )

        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_dir, capture_output=True, check=True)

        # User changes same line
        config_file.write_text("setting=user_value")
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "User changes"], cwd=project_dir, capture_output=True, check=True)

        # Update (recipe changes to value2)
        client = UpdateClient(recipe_backend)
        result = client.update_project(
            project_path=project_dir, target_version="v2.0.0", diff_mode=DiffMode.THREE_WAY, dry_run=False
        )

        # Should detect conflict
        assert len(result.files_with_conflicts) > 0 or "<<<<<<" in config_file.read_text()

    def test_update_project_dry_run_no_changes(self, recipe_backend, tmp_path):
        """Test dry run doesn't modify files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Setup git
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, capture_output=True)

        # Create initial files
        readme = project_dir / "README.md"
        readme.write_text("# my_project\n\nVersion 1.0.0")

        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
              recipe_name: test_recipe
              docker_image: test/test_recipe:v1.0.0
            """
        )

        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_dir, capture_output=True, check=True)

        original_content = readme.read_text()

        # Dry run update
        client = UpdateClient(recipe_backend)
        client.update_project(
            project_path=project_dir, target_version="v2.0.0", diff_mode=DiffMode.THREE_WAY, dry_run=True
        )

        # Files should not change
        assert readme.read_text() == original_content
        assert not (project_dir / "CHANGELOG.md").exists()

    def test_update_project_two_way_merge(self, recipe_backend, tmp_path):
        """Test 2-way merge overwrites files."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Setup git
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, capture_output=True)

        # Create initial files
        config_file = project_dir / "config.txt"
        config_file.write_text("setting=value1")

        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
              recipe_name: test_recipe
              docker_image: test/test_recipe:v1.0.0
            """
        )

        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_dir, capture_output=True, check=True)

        # Update with 2-way merge
        client = UpdateClient(recipe_backend)
        result = client.update_project(
            project_path=project_dir, target_version="v2.0.0", diff_mode=DiffMode.TWO_WAY, dry_run=False
        )

        assert result.success or len(result.errors) == 0

        # File should be overwritten
        assert "value2" in config_file.read_text()
        assert (project_dir / "CHANGELOG.md").exists()

    def test_check_update_available_finds_newer_version(self, recipe_backend, tmp_path):
        """Test checking for updates finds newer version."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
              recipe_name: test_recipe
              docker_image: test/test_recipe:v1.0.0
            """
        )

        client = UpdateClient(recipe_backend)
        latest = client.check_update_available(project_dir)

        assert latest == "v2.0.0"

    def test_check_update_available_no_update_needed(self, recipe_backend, tmp_path):
        """Test checking for updates when already on latest."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text(
            """metadata:
  recipe_name: test_recipe
  docker_image: test/test_recipe:v2.0.0
"""
        )

        client = UpdateClient(recipe_backend)
        latest = client.check_update_available(project_dir)

        assert latest is None
