"""Local filesystem backend for recipes."""

from pathlib import Path

from nskit.client.backends.base import RecipeBackend
from nskit.client.models import RecipeInfo


class LocalBackend(RecipeBackend):
    """Backend for local filesystem recipes."""

    def __init__(self, recipes_dir: Path, entrypoint: str = "nskit.recipes"):
        """Initialize local backend.

        Args:
            recipes_dir: Directory containing recipes.
            entrypoint: Recipe entrypoint name.
        """
        self.recipes_dir = Path(recipes_dir)
        self._entrypoint = entrypoint

    @property
    def entrypoint(self) -> str:
        """Get the recipe entrypoint."""
        return self._entrypoint

    def list_recipes(self) -> list[RecipeInfo]:
        """List recipes from local directory.

        Returns:
            List of recipe information found in the recipes directory.
        """
        recipes = []
        if not self.recipes_dir.exists():
            return recipes

        for recipe_dir in self.recipes_dir.iterdir():
            if recipe_dir.is_dir() and not recipe_dir.name.startswith("."):
                versions = []
                for version_dir in recipe_dir.iterdir():
                    if version_dir.is_dir() and not version_dir.name.startswith("."):
                        versions.append(version_dir.name)
                if versions:
                    recipes.append(
                        RecipeInfo(
                            name=recipe_dir.name,
                            versions=sorted(versions),
                            description=f"Local recipe: {recipe_dir.name}",
                        )
                    )
        return recipes

    def get_recipe_versions(self, recipe: str) -> list[str]:
        """Get versions for a recipe.

        Args:
            recipe: Recipe name.

        Returns:
            Sorted list of version strings.
        """
        recipe_dir = self.recipes_dir / recipe
        if not recipe_dir.exists():
            return []
        versions = []
        for version_dir in recipe_dir.iterdir():
            if version_dir.is_dir() and not version_dir.name.startswith("."):
                versions.append(version_dir.name)
        return sorted(versions)

    def fetch_recipe(self, recipe: str, version: str, dest: Path) -> Path:
        """Copy recipe from local directory.

        Args:
            recipe: Recipe name.
            version: Recipe version.
            dest: Destination directory.

        Returns:
            Path to the copied recipe.

        Raises:
            FileNotFoundError: If the recipe version does not exist.
        """
        import shutil

        source = self.recipes_dir / recipe / version
        if not source.exists():
            raise FileNotFoundError(f"Recipe {recipe} version {version} not found at {source}")
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest / recipe, dirs_exist_ok=True)
        return dest / recipe
