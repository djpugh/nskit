"""Utilities for reading nskit labels from Docker images."""
from __future__ import annotations

import subprocess  # nosec B404

LABEL_RECIPE = "nskit.recipe"
LABEL_RECIPE_NAME = "nskit.recipe.name"


def get_recipe_name_from_image(image_url: str) -> str | None:
    """Read the ``nskit.recipe.name`` label from a Docker image.

    Works on locally available images (already pulled or built).
    Returns ``None`` if the image isn't available or has no label.
    """
    result = subprocess.run(  # nosec B603, B607
        ["docker", "inspect", image_url, "--format", f'{{{{index .Config.Labels "{LABEL_RECIPE_NAME}"}}}}'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        name = result.stdout.strip()
        if name and name != "<no value>":
            return name
    return None


def is_nskit_recipe_image(image_url: str) -> bool:
    """Check if a Docker image has the ``nskit.recipe=true`` label."""
    result = subprocess.run(  # nosec B603, B607
        ["docker", "inspect", image_url, "--format", f'{{{{index .Config.Labels "{LABEL_RECIPE}"}}}}'],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"
