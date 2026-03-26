"""Recipe client for programmatic recipe operations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from nskit.client.backends.base import RecipeBackend
from nskit.client.engines import DockerEngine, RecipeEngine
from nskit.client.models import RecipeInfo, RecipeResult


def _read_recipe_label(image_url: str) -> str | None:
    """Read nskit.recipe.name label from a pulled Docker image."""
    from nskit.client.backends.image_labels import get_recipe_name, read_local_labels

    return get_recipe_name(read_local_labels(image_url))


class RecipeClient:
    """Pure Python client for recipe operations (no CLI dependencies)."""

    def __init__(self, backend: RecipeBackend, engine: RecipeEngine | None = None):
        """Initialize the recipe client.

        Args:
            backend: Backend for recipe discovery and fetching
            engine: Execution engine (defaults to DockerEngine)
        """
        self.backend = backend
        self.engine = engine or DockerEngine()

    def list_recipes(self) -> list[RecipeInfo]:
        """List all available recipes from the backend.

        Returns:
            List of recipe information
        """
        return self.backend.list_recipes()

    def get_recipe_versions(self, recipe: str) -> list[str]:
        """Get available versions for a specific recipe.

        Args:
            recipe: Recipe name

        Returns:
            List of available versions
        """
        return self.backend.get_recipe_versions(recipe)

    def initialize_recipe(
        self,
        recipe: str,
        version: str,
        parameters: dict[str, Any],
        output_dir: Path,
        force: bool = False,
    ) -> RecipeResult:
        """Initialize a new project from a recipe.

        Args:
            recipe: Recipe name
            version: Recipe version
            parameters: Recipe parameters
            output_dir: Output directory for the project
            force: Allow initialization in non-empty directory

        Returns:
            Result of the initialization
        """
        errors = []

        # Check output directory
        if output_dir.exists() and any(output_dir.iterdir()) and not force:
            errors.append(f"Output directory {output_dir} is not empty. Use force=True to override.")
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
            )

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get image URL from backend (only if backend supports it and engine needs it)
            image_url = None
            if hasattr(self.engine, "__class__") and self.engine.__class__.__name__ == "DockerEngine":
                if hasattr(self.backend, "get_image_url"):
                    image_url = self.backend.get_image_url(recipe, version)
                    if hasattr(self.backend, "pull_image"):
                        self.backend.pull_image(image_url)
                    # Read canonical recipe name from image label
                    recipe = _read_recipe_label(image_url) or recipe

            # Execute using engine
            return self.engine.execute(
                recipe=recipe,
                version=version,
                parameters=parameters,
                output_dir=output_dir,
                image_url=image_url,
                entrypoint=self.backend.entrypoint,
            )

        except Exception as e:
            errors.append(str(e))
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
            )
