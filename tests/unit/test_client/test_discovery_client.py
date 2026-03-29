"""Unit tests for DiscoveryClient."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from nskit.client.discovery import DiscoveryClient
from nskit.client.models import RecipeInfo


class TestDiscoverRecipes(unittest.TestCase):
    """Tests for DiscoveryClient.discover_recipes."""

    def _make_backend(self) -> MagicMock:
        """Create a mock backend with sample recipes."""
        backend = MagicMock()
        backend.list_recipes.return_value = [
            RecipeInfo(name="python-api", versions=["1.0.0"], description="A Python API template"),
            RecipeInfo(name="react-app", versions=["2.0.0"], description="A React application"),
            RecipeInfo(name="go-service", versions=["1.0.0"], description="A Go microservice"),
        ]
        return backend

    def test_returns_all_without_search(self) -> None:
        """Returns all recipes when no search term is provided."""
        backend = self._make_backend()
        client = DiscoveryClient(backend)
        recipes = client.discover_recipes()
        self.assertEqual(len(recipes), 3)

    def test_filters_by_name(self) -> None:
        """Filters recipes by name match."""
        backend = self._make_backend()
        client = DiscoveryClient(backend)
        recipes = client.discover_recipes(search_term="python")
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].name, "python-api")

    def test_filters_by_description(self) -> None:
        """Filters recipes by description match."""
        backend = self._make_backend()
        client = DiscoveryClient(backend)
        recipes = client.discover_recipes(search_term="microservice")
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0].name, "go-service")

    def test_case_insensitive_search(self) -> None:
        """Search is case-insensitive."""
        backend = self._make_backend()
        client = DiscoveryClient(backend)
        recipes = client.discover_recipes(search_term="REACT")
        self.assertEqual(len(recipes), 1)

    def test_no_matches_returns_empty(self) -> None:
        """Returns empty list when nothing matches."""
        backend = self._make_backend()
        client = DiscoveryClient(backend)
        recipes = client.discover_recipes(search_term="rust")
        self.assertEqual(len(recipes), 0)


class TestGetRecipeInfo(unittest.TestCase):
    """Tests for DiscoveryClient.get_recipe_info."""

    def test_returns_matching_recipe(self) -> None:
        """Returns the recipe matching the given name."""
        backend = MagicMock()
        backend.list_recipes.return_value = [
            RecipeInfo(name="alpha", versions=["1.0.0"]),
            RecipeInfo(name="beta", versions=["2.0.0"]),
        ]
        client = DiscoveryClient(backend)
        info = client.get_recipe_info("beta")
        self.assertIsNotNone(info)
        self.assertEqual(info.name, "beta")

    def test_returns_none_when_not_found(self) -> None:
        """Returns None when no recipe matches."""
        backend = MagicMock()
        backend.list_recipes.return_value = []
        client = DiscoveryClient(backend)
        self.assertIsNone(client.get_recipe_info("missing"))


class TestGetRecipeVersions(unittest.TestCase):
    """Tests for DiscoveryClient.get_recipe_versions."""

    def test_delegates_to_backend(self) -> None:
        """Passes through to backend.get_recipe_versions."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0", "2.0.0"]
        client = DiscoveryClient(backend)
        versions = client.get_recipe_versions("recipe")
        self.assertEqual(versions, ["1.0.0", "2.0.0"])
        backend.get_recipe_versions.assert_called_once_with("recipe")


if __name__ == "__main__":
    unittest.main()
