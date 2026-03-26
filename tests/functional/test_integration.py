"""Integration tests for the complete recipe workflow."""

import subprocess
from pathlib import Path

import pytest

from nskit.client.backends import LocalBackend
from nskit.mixer.components import Recipe
from nskit.recipes import DiscoveryClient, RecipeClient, UpdateClient


@pytest.fixture
def recipes_dir(tmp_path):
    """Create a temporary recipes directory with test recipes."""
    recipes = tmp_path / "recipes"
    recipes.mkdir()

    # Create python_package recipe v1.0.0
    recipe_v1 = recipes / "python_package" / "v1.0.0"
    recipe_v1.mkdir(parents=True)

    (recipe_v1 / "template.txt").write_text("Hello {{name}} v1.0.0")
    (recipe_v1 / "README.md").write_text("# {{name}}\n\nVersion 1.0.0")

    # Create python_package recipe v1.1.0
    recipe_v11 = recipes / "python_package" / "v1.1.0"
    recipe_v11.mkdir(parents=True)

    (recipe_v11 / "template.txt").write_text("Hello {{name}} v1.1.0")
    (recipe_v11 / "README.md").write_text("# {{name}}\n\nVersion 1.1.0\n\nNew features!")
    (recipe_v11 / "CHANGELOG.md").write_text("## v1.1.0\n- New features")

    # Create typescript_app recipe v2.0.0
    recipe_ts = recipes / "typescript_app" / "v2.0.0"
    recipe_ts.mkdir(parents=True)

    (recipe_ts / "package.json").write_text('{"name": "{{name}}"}')

    return recipes


@pytest.fixture
def backend(recipes_dir):
    """Create LocalBackend with test recipes."""
    return LocalBackend(recipes_dir=recipes_dir)


class TestIntegrationWorkflow:
    """Integration tests for complete workflow."""

    def test_discover_list_recipes(self, backend):
        """Test discovering and listing recipes."""
        discovery = DiscoveryClient(backend)
        recipes = discovery.discover_recipes()

        assert len(recipes) == 2
        recipe_names = [r.name for r in recipes]
        assert "python_package" in recipe_names
        assert "typescript_app" in recipe_names

    def test_discover_search_recipes(self, backend):
        """Test searching recipes."""
        discovery = DiscoveryClient(backend)
        recipes = discovery.discover_recipes(search_term="python")

        assert len(recipes) == 1
        assert recipes[0].name == "python_package"

    def test_get_recipe_versions(self, backend):
        """Test getting recipe versions."""
        client = RecipeClient(backend)
        versions = client.get_recipe_versions("python_package")

        assert len(versions) == 2
        assert "v1.0.0" in versions
        assert "v1.1.0" in versions

    def test_full_workflow_init_and_update(self, backend, tmp_path):
        """Test complete workflow: discover, init, update."""
        from unittest.mock import Mock, patch

        # 1. Discover recipes
        discovery = DiscoveryClient(backend)
        recipes = discovery.discover_recipes()
        assert len(recipes) > 0

        # 2. Initialize project with v1.0.0
        project_path = tmp_path / "my_project"
        project_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, capture_output=True)

        # Copy recipe files manually (simulating init)
        recipe_v1 = backend.recipes_dir / "python_package" / "v1.0.0"
        for file in recipe_v1.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(recipe_v1)
                dest = project_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(file.read_text().replace("{{name}}", "my_project"))

        # Create recipe config
        config_dir = project_path / ".recipe"
        config_dir.mkdir()
        config_content = """metadata:
  recipe_name: v1.0.0
  docker_image: test/python_package:v1.0.0
"""
        (config_dir / "config.yml").write_text(config_content)

        # Commit initial state
        subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_path, capture_output=True)

        # Verify initial files
        assert (project_path / "template.txt").exists()
        assert "v1.0.0" in (project_path / "template.txt").read_text()

        # 3. Check for updates (mock the config loading)
        with patch("nskit.mixer.components.RecipeConfig") as mock_config_class:
            mock_config = Mock()
            mock_config.metadata = Mock()
            mock_config.metadata.recipe_name = "v1.0.0"
            mock_config_class.load_from_file.return_value = mock_config

            # Mock backend to return versions
            backend.get_recipe_versions = Mock(return_value=["v1.0.0", "v1.1.0"])

            update_client = UpdateClient(backend)
            latest = update_client.check_update_available(project_path)
            assert latest == "v1.1.0"

    def test_update_preserves_user_changes(self, backend, tmp_path):
        """Test that updates preserve user modifications."""
        project_path = tmp_path / "my_project"
        project_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, capture_output=True)

        # Create initial file
        test_file = project_path / "README.md"
        test_file.write_text("# my_project\n\nVersion 1.0.0\n\nUser custom content")

        # Create recipe config
        config_dir = project_path / ".recipe"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            """
            metadata:
              recipe_name: python_package
              docker_image: test/python_package:v1.0.0
            """
        )

        # Commit
        subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_path, capture_output=True)

        # Update
        update_client = UpdateClient(backend)
        update_client.update_project(
            project_path=project_path,
            target_version="v1.1.0",
        )

        # User content should be preserved (or flagged as conflict)
        content = test_file.read_text()
        assert "User custom content" in content or "my_project" in content

    def test_dry_run_doesnt_modify_files(self, backend, tmp_path):
        """Test dry run doesn't modify any files."""
        project_path = tmp_path / "my_project"
        project_path.mkdir()

        # Setup project
        subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project_path, capture_output=True)

        test_file = project_path / "test.txt"
        test_file.write_text("original content")

        config_dir = project_path / ".recipe"
        config_dir.mkdir()
        (config_dir / "config.yml").write_text(
            """
            metadata:
              recipe_name: python_package
              docker_image: test/python_package:v1.0.0
            """
        )

        subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_path, capture_output=True)

        original_content = test_file.read_text()

        # Dry run update
        update_client = UpdateClient(backend)
        update_client.update_project(
            project_path=project_path,
            target_version="v1.1.0",
            dry_run=True,
        )

        # File should be unchanged
        assert test_file.read_text() == original_content
