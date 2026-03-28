"""Local execution engine."""

from pathlib import Path
from typing import Any

from nskit.client.engines.base import RecipeEngine
from nskit.client.models import RecipeResult
from nskit.mixer.components import Recipe


class LocalEngine(RecipeEngine):
    """Execute recipes from locally installed packages."""

    def execute(
        self,
        recipe: str,
        version: str,
        parameters: dict[str, Any],
        output_dir: Path,
        image_url: str = None,
        entrypoint: str = None,
    ) -> RecipeResult:
        """Execute recipe from installed package.

        Args:
            recipe: Recipe name.
            version: Recipe version.
            parameters: Recipe parameters.
            output_dir: Output directory.
            image_url: Not used for Local engine.
            entrypoint: Recipe entrypoint (required).

        Returns:
            Recipe execution result.
        """
        if not entrypoint:
            raise ValueError("Local engine requires entrypoint")

        errors = []
        warnings: list[str] = []

        try:
            recipe_instance = Recipe.load(recipe, entrypoint=entrypoint, **parameters)
            result = recipe_instance.create(base_path=output_dir.parent, override_path=output_dir.name)
            files_created = list(result.keys()) if result else []

            return RecipeResult(
                success=True,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                files_created=files_created,
                warnings=warnings,
            )

        except Exception as e:
            errors.append(str(e))
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
                warnings=warnings,
            )
