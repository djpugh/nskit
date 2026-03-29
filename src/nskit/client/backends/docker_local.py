"""Docker local backend — discovers recipes from locally pulled Docker images.

Images are discovered by filtering on the ``nskit.recipe`` label.
Build recipe images with these labels:

    docker build \\
        --label nskit.recipe=true \\
        --label nskit.recipe.name=python_package \\
        --label nskit.recipe.entrypoint=mycompany.recipes \\
        -t myorg/python_package:v1.0.0 .
"""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path

from nskit.client.backends.base import RecipeBackend
from nskit.client.models import RecipeInfo
from nskit.constants import RECIPE_ENTRYPOINT

LABEL_PREFIX = "nskit.recipe"


class DockerLocalBackend(RecipeBackend):
    """Backend that discovers recipes from locally available Docker images.

    Filters images by the ``nskit.recipe=true`` label. Each image must
    also have ``nskit.recipe.name`` set. Versions are derived from image
    tags.

    Args:
        entrypoint: Recipe entry point group name.
        label_filter: Label to filter images (default ``nskit.recipe=true``).
    """

    def __init__(
        self,
        entrypoint: str = RECIPE_ENTRYPOINT,
        label_filter: str = f"{LABEL_PREFIX}=true",
    ) -> None:
        self._entrypoint = entrypoint
        self._label_filter = label_filter

    @property
    def entrypoint(self) -> str:
        """Get the recipe entrypoint."""
        return self._entrypoint

    def _query_images(self) -> list[dict[str, str]]:
        """Query Docker for images matching the label filter.

        Returns:
            List of dicts with ``repository``, ``tag``, and ``name`` keys.
        """
        from nskit.client.backends.image_labels import get_recipe_name, read_local_labels

        result = subprocess.run(  # nosec B603, B607
            [
                "docker",
                "images",
                "--filter",
                f"label={self._label_filter}",
                "--format",
                "{{.Repository}}\t{{.Tag}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        images = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1] != "<none>":
                image_ref = f"{parts[0]}:{parts[1]}"
                labels = read_local_labels(image_ref)
                name = get_recipe_name(labels) or parts[0].rsplit("/", 1)[-1]
                images.append({"repository": parts[0], "tag": parts[1], "name": name})
        return images

    def list_recipes(self) -> list[RecipeInfo]:
        """List recipes from locally pulled Docker images.

        Returns:
            List of recipe information from local images.
        """
        images = self._query_images()
        recipes: dict[str, list[str]] = {}
        for img in images:
            recipes.setdefault(img["name"], []).append(img["tag"])
        return [RecipeInfo(name=name, versions=sorted(versions, reverse=True)) for name, versions in recipes.items()]

    def get_recipe_versions(self, recipe: str) -> list[str]:
        """Get versions for a recipe from local image tags.

        Args:
            recipe: Recipe name.

        Returns:
            Sorted list of version strings (newest first).
        """
        images = self._query_images()
        return sorted([img["tag"] for img in images if img["name"] == recipe], reverse=True)

    def fetch_recipe(self, recipe: str, version: str, dest: Path) -> Path:
        """Not used — Docker images are executed directly.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError("DockerLocalBackend executes images directly")

    def get_image_url(self, recipe: str, version: str) -> str:
        """Get the full image:tag for a recipe version.

        Args:
            recipe: Recipe name.
            version: Recipe version.

        Returns:
            Full image reference string.

        Raises:
            ValueError: If no matching local image is found.
        """
        images = self._query_images()
        for img in images:
            if img["name"] == recipe and img["tag"] == version:
                return f"{img['repository']}:{img['tag']}"
        raise ValueError(f"No local image found for {recipe}:{version}")

    def pull_image(self, image_url: str) -> None:
        """No-op — images are already local."""
