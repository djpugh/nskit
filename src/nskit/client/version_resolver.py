"""Version resolution for recipes from backends."""

from __future__ import annotations

from nskit.client.backends.base import RecipeBackend
from nskit.client.exceptions import UpdateError


class VersionResolver:
    """Resolves recipe versions from backends.

    Args:
        backend: Recipe backend to query for versions.
    """

    def __init__(self, backend: RecipeBackend) -> None:
        self.backend = backend

    def resolve_version(self, recipe_name: str, target_version: str | None = None) -> str:
        """Resolve a recipe version.

        When *target_version* is ``None``, resolves to the latest available
        version. When specified, validates that the version exists.

        Args:
            recipe_name: Name of the recipe.
            target_version: Desired version, or ``None`` for latest.

        Returns:
            The resolved version string.

        Raises:
            UpdateError: If no versions are available or the requested
                version does not exist.
        """
        versions = self.get_available_versions(recipe_name)
        if not versions:
            raise UpdateError(f"No versions available for recipe '{recipe_name}'")

        if target_version is None:
            return versions[-1]

        if target_version not in versions:
            raise UpdateError(
                f"Version '{target_version}' not found for recipe '{recipe_name}'",
                details=f"Available versions: {', '.join(versions)}",
            )
        return target_version

    def get_available_versions(self, recipe_name: str) -> list[str]:
        """Retrieve the full list of available versions from the backend.

        Args:
            recipe_name: Name of the recipe.

        Returns:
            List of version strings as returned by the backend.
        """
        return self.backend.get_recipe_versions(recipe_name)

    def check_update_needed(
        self,
        recipe_name: str,
        current_version: str,
        target_version: str | None = None,
    ) -> tuple[bool, str]:
        """Check whether an update is needed.

        Args:
            recipe_name: Name of the recipe.
            current_version: Currently installed version.
            target_version: Desired version, or ``None`` for latest.

        Returns:
            Tuple of ``(update_needed, resolved_version)``.
        """
        resolved = self.resolve_version(recipe_name, target_version)
        return (resolved != current_version, resolved)
