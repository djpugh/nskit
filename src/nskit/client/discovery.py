"""Discovery client for finding recipes."""
from typing import List, Optional

from nskit.client.backends.base import RecipeBackend
from nskit.client.models import RecipeInfo


class DiscoveryClient:
    """Client for discovering available recipes."""

    def __init__(self, backend: RecipeBackend):
        """Initialize discovery client.

        Args:
            backend: Backend for recipe discovery
        """
        self.backend = backend

    def discover_recipes(
        self,
        search_term: Optional[str] = None,
    ) -> List[RecipeInfo]:
        """Discover available recipes.

        Args:
            search_term: Optional search term to filter recipes

        Returns:
            List of discovered recipes
        """
        recipes = self.backend.list_recipes()

        if search_term:
            search_lower = search_term.lower()
            recipes = [
                r
                for r in recipes
                if search_lower in r.name.lower() or (r.description and search_lower in r.description.lower())
            ]

        return recipes

    def get_recipe_info(self, recipe_name: str) -> Optional[RecipeInfo]:
        """Get detailed info for a specific recipe.

        Args:
            recipe_name: Recipe name

        Returns:
            Recipe info or None if not found
        """
        recipes = self.backend.list_recipes()

        for recipe in recipes:
            if recipe.name == recipe_name:
                return recipe

        return None

    def get_recipe_versions(self, recipe_name: str) -> List[str]:
        """Get available versions for a recipe.

        Args:
            recipe_name: Recipe name

        Returns:
            List of available versions
        """
        return self.backend.get_recipe_versions(recipe_name)
