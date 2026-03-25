"""Project generator for diff comparison."""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from nskit.client.backends.base import RecipeBackend
from nskit.client.config import RecipeConfig
from nskit.client.diff.models import DiffMode
from nskit.client.engines.base import RecipeEngine
from nskit.client.exceptions import UpdateError


class ProjectGenerator:
    """Generates project versions from recipe images for diff comparison.

    Args:
        backend: Recipe backend for fetching recipe data.
        engine: Recipe engine for executing recipes.
    """

    def __init__(self, backend: RecipeBackend, engine: RecipeEngine) -> None:
        self.backend = backend
        self.engine = engine

    def generate_project_states(
        self,
        config: RecipeConfig,
        target_version: str,
        current_project_path: Path,
        diff_mode: DiffMode,
    ) -> tuple[Path, Path | None, Path]:
        """Generate project states for diff comparison.

        Args:
            config: Current recipe configuration.
            target_version: Version to update to.
            current_project_path: Path to the current project.
            diff_mode: Whether to use 2-way or 3-way comparison.

        Returns:
            Tuple of ``(current_project, old_fresh, new_fresh)``.
            ``old_fresh`` is ``None`` in ``TWO_WAY`` mode.

        Raises:
            UpdateError: If generation fails.
        """
        if config.metadata is None:
            raise UpdateError("Cannot generate project states without recipe metadata")

        recipe_name = config.metadata.recipe_name
        parameters = dict(config.input)
        current_image = config.metadata.docker_image

        new_image = self._replace_version_tag(current_image, target_version)
        new_fresh = Path(tempfile.mkdtemp(prefix="nskit_new_"))

        old_fresh: Path | None = None
        if diff_mode == DiffMode.THREE_WAY:
            current_version = self._extract_version_tag(current_image)
            old_fresh = Path(tempfile.mkdtemp(prefix="nskit_old_"))
            self.generate_version(
                recipe_name,
                current_version,
                parameters,
                old_fresh,
                image_url=current_image,
            )

        self.generate_version(
            recipe_name,
            target_version,
            parameters,
            new_fresh,
            image_url=new_image,
        )

        return current_project_path, old_fresh, new_fresh

    def generate_version(
        self,
        recipe_name: str,
        version: str,
        parameters: dict[str, Any],
        output_path: Path,
        image_url: str | None = None,
    ) -> None:
        """Generate a project version using the recipe engine.

        Args:
            recipe_name: Name of the recipe.
            version: Recipe version to generate.
            parameters: Input parameters for the recipe.
            output_path: Directory to write the generated project into.
            image_url: Optional Docker image URL override.

        Raises:
            UpdateError: If the engine execution fails.
        """
        try:
            self.engine.execute(
                recipe=recipe_name,
                version=version,
                parameters=parameters,
                output_dir=output_path,
                image_url=image_url,
                entrypoint=getattr(self.backend, "entrypoint", None),
            )
        except Exception as exc:
            raise UpdateError(
                f"Failed to generate project version '{version}'",
                details=str(exc),
            ) from exc

    def cleanup_states(self, *paths: Path) -> None:
        """Clean up temporary directories.

        Args:
            paths: Paths to remove. ``None`` values are silently skipped.
        """
        for path in paths:
            if path is not None and path.exists():
                shutil.rmtree(path, ignore_errors=True)

    def _replace_version_tag(self, image_url: str, new_version: str) -> str:
        """Replace the version tag in a Docker image URL."""
        return re.sub(r":[^/]+$", f":{new_version}", image_url)

    def _extract_version_tag(self, image_url: str) -> str:
        """Extract the version tag from a Docker image URL."""
        match = re.search(r":([^/]+)$", image_url)
        if match:
            return match.group(1)
        return "latest"
