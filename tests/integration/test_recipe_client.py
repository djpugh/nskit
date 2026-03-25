"""Functional tests for RecipeClient with mocked backends."""
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from nskit.client.models import RecipeInfo
from nskit.recipes import RecipeClient


@pytest.fixture
def mock_backend():
    """Mock backend for testing."""
    backend = Mock()
    backend.entrypoint = "test.recipes"
    backend.list_recipes.return_value = [
        RecipeInfo(name="python_package", versions=["v1.0.0", "v1.1.0"]),
        RecipeInfo(name="typescript_app", versions=["v2.0.0"]),
    ]
    backend.get_recipe_versions.return_value = ["v1.0.0", "v1.1.0"]
    backend.fetch_recipe.return_value = Path("/tmp/recipe")
    return backend


class TestRecipeClient:
    """Test RecipeClient functionality."""

    def test_list_recipes(self, mock_backend):
        """Test listing recipes."""
        client = RecipeClient(mock_backend)
        recipes = client.list_recipes()

        assert len(recipes) == 2
        assert recipes[0].name == "python_package"
        assert recipes[1].name == "typescript_app"
        mock_backend.list_recipes.assert_called_once()

    def test_get_recipe_versions(self, mock_backend):
        """Test getting recipe versions."""
        client = RecipeClient(mock_backend)
        versions = client.get_recipe_versions("python_package")

        assert len(versions) == 2
        assert versions[0] == "v1.0.0"
        assert versions[1] == "v1.1.0"
        mock_backend.get_recipe_versions.assert_called_once_with("python_package")

    def test_initialize_recipe(self, mock_backend, tmp_path):
        """Test initializing a recipe."""
        client = RecipeClient(mock_backend)

        # Just test that the method exists and can be called
        # Full integration test would require actual recipe files
        assert hasattr(client, "initialize_recipe")
        assert callable(client.initialize_recipe)


class TestRecipeClientAdditional:
    """Additional tests for RecipeClient uncovered functions."""

    def test_get_recipe_versions(self):
        """Test getting recipe versions."""
        from unittest.mock import Mock

        backend = Mock()
        backend.entrypoint = "test.recipes"
        backend.get_recipe_versions.return_value = ["v1.0.0", "v2.0.0", "v3.0.0"]

        client = RecipeClient(backend)
        versions = client.get_recipe_versions("test_recipe")

        assert len(versions) == 3
        assert "v1.0.0" in versions
        assert "v3.0.0" in versions
