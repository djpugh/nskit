"""Backend interface for recipe discovery and fetching."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from nskit.client.models import RecipeInfo


class RecipeBackend(ABC):
    """Abstract interface for recipe backends."""

    @property
    @abstractmethod
    def entrypoint(self) -> str:
        """Get the recipe entrypoint for this backend."""
        pass

    @abstractmethod
    def list_recipes(self) -> list[RecipeInfo]:
        """List all available recipes.

        Returns:
            List of recipe information.
        """
        pass

    @abstractmethod
    def get_recipe_versions(self, recipe: str) -> list[str]:
        """Get available versions for a recipe.

        Args:
            recipe: Recipe name.

        Returns:
            List of version strings.
        """
        pass

    @abstractmethod
    def fetch_recipe(self, recipe: str, version: str, dest: Path) -> Path:
        """Fetch a recipe to a destination directory.

        Args:
            recipe: Recipe name.
            version: Recipe version.
            dest: Destination directory.

        Returns:
            Path to the fetched recipe.
        """
        pass

    def get_recipe_metadata(self, recipe: str, version: str) -> dict[str, Any]:
        """Get metadata for a specific recipe version.

        Args:
            recipe: Recipe name.
            version: Recipe version.

        Returns:
            Recipe metadata dictionary.
        """
        return {}

    def get_image_url(self, recipe: str, version: str) -> str:
        """Get Docker image URL for a recipe.

        Args:
            recipe: Recipe name.
            version: Recipe version.

        Returns:
            Docker image URL.
        """
        raise NotImplementedError("This backend does not support Docker images")

    def pull_image(self, image_url: str) -> None:
        """Pull Docker image.

        Args:
            image_url: Docker image URL to pull.
        """
        raise NotImplementedError("This backend does not support Docker images")
