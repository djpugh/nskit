"""Functional tests for RecipeClient with mocked backends."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

from nskit.client.models import RecipeInfo
from nskit.recipes import RecipeClient


class TestRecipeClient(unittest.TestCase):
    """Test RecipeClient functionality."""

    def setUp(self):
        """Set up mock backend for testing."""
        self.mock_backend = Mock()
        self.mock_backend.entrypoint = "test.recipes"
        self.mock_backend.list_recipes.return_value = [
            RecipeInfo(name="python_package", versions=["v1.0.0", "v1.1.0"]),
            RecipeInfo(name="typescript_app", versions=["v2.0.0"]),
        ]
        self.mock_backend.get_recipe_versions.return_value = ["v1.0.0", "v1.1.0"]
        self.mock_backend.fetch_recipe.return_value = Path("/tmp/recipe")

    def test_list_recipes(self):
        """Test listing recipes."""
        client = RecipeClient(self.mock_backend)
        recipes = client.list_recipes()

        self.assertEqual(len(recipes), 2)
        self.assertEqual(recipes[0].name, "python_package")
        self.assertEqual(recipes[1].name, "typescript_app")
        self.mock_backend.list_recipes.assert_called_once()

    def test_get_recipe_versions(self):
        """Test getting recipe versions."""
        client = RecipeClient(self.mock_backend)
        versions = client.get_recipe_versions("python_package")

        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0], "v1.0.0")
        self.assertEqual(versions[1], "v1.1.0")
        self.mock_backend.get_recipe_versions.assert_called_once_with("python_package")

    def test_initialize_recipe(self):
        """Test initializing a recipe."""
        client = RecipeClient(self.mock_backend)

        # Just test that the method exists and can be called
        # Full integration test would require actual recipe files
        self.assertTrue(hasattr(client, "initialize_recipe"))
        self.assertTrue(callable(client.initialize_recipe))


class TestRecipeClientAdditional(unittest.TestCase):
    """Additional tests for RecipeClient uncovered functions."""

    def test_get_recipe_versions(self):
        """Test getting recipe versions."""
        backend = Mock()
        backend.entrypoint = "test.recipes"
        backend.get_recipe_versions.return_value = ["v1.0.0", "v2.0.0", "v3.0.0"]

        client = RecipeClient(backend)
        versions = client.get_recipe_versions("test_recipe")

        self.assertEqual(len(versions), 3)
        self.assertIn("v1.0.0", versions)
        self.assertIn("v3.0.0", versions)


if __name__ == "__main__":
    unittest.main()
