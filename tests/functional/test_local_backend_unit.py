"""Unit tests for LocalBackend."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from nskit.client.backends.local import LocalBackend


class TestLocalBackendListRecipes(unittest.TestCase):
    """Tests for LocalBackend.list_recipes."""

    def test_lists_recipes_from_directory(self) -> None:
        """Discovers recipes from subdirectories with version folders."""
        with TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp)
            (recipes_dir / "recipe-a" / "1.0.0").mkdir(parents=True)
            (recipes_dir / "recipe-a" / "2.0.0").mkdir(parents=True)
            (recipes_dir / "recipe-b" / "0.1.0").mkdir(parents=True)

            backend = LocalBackend(recipes_dir=recipes_dir)
            recipes = backend.list_recipes()

            names = {r.name for r in recipes}
            self.assertEqual(names, {"recipe-a", "recipe-b"})

    def test_empty_directory_returns_empty(self) -> None:
        """Returns empty list when recipes directory is empty."""
        with TemporaryDirectory() as tmp:
            backend = LocalBackend(recipes_dir=Path(tmp))
            self.assertEqual(backend.list_recipes(), [])

    def test_nonexistent_directory_returns_empty(self) -> None:
        """Returns empty list when recipes directory does not exist."""
        backend = LocalBackend(recipes_dir=Path("/nonexistent/path"))
        self.assertEqual(backend.list_recipes(), [])

    def test_hidden_directories_ignored(self) -> None:
        """Directories starting with '.' are excluded."""
        with TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp)
            (recipes_dir / ".hidden" / "1.0.0").mkdir(parents=True)
            (recipes_dir / "visible" / "1.0.0").mkdir(parents=True)

            backend = LocalBackend(recipes_dir=recipes_dir)
            names = [r.name for r in backend.list_recipes()]
            self.assertEqual(names, ["visible"])


class TestLocalBackendGetRecipeVersions(unittest.TestCase):
    """Tests for LocalBackend.get_recipe_versions."""

    def test_returns_sorted_versions(self) -> None:
        """Versions are returned in sorted order."""
        with TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp)
            (recipes_dir / "recipe" / "2.0.0").mkdir(parents=True)
            (recipes_dir / "recipe" / "1.0.0").mkdir(parents=True)

            backend = LocalBackend(recipes_dir=recipes_dir)
            versions = backend.get_recipe_versions("recipe")
            self.assertEqual(versions, ["1.0.0", "2.0.0"])

    def test_nonexistent_recipe_returns_empty(self) -> None:
        """Returns empty list for a recipe that does not exist."""
        with TemporaryDirectory() as tmp:
            backend = LocalBackend(recipes_dir=Path(tmp))
            self.assertEqual(backend.get_recipe_versions("nope"), [])


class TestLocalBackendFetchRecipe(unittest.TestCase):
    """Tests for LocalBackend.fetch_recipe."""

    def test_copies_recipe_to_destination(self) -> None:
        """Recipe files are copied to the destination directory."""
        with TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp) / "recipes"
            version_dir = recipes_dir / "my-recipe" / "1.0.0"
            version_dir.mkdir(parents=True)
            (version_dir / "template.txt").write_text("hello")

            dest = Path(tmp) / "dest"
            backend = LocalBackend(recipes_dir=recipes_dir)
            result = backend.fetch_recipe("my-recipe", "1.0.0", dest)

            self.assertTrue((result / "template.txt").exists())

    def test_missing_version_raises(self) -> None:
        """Raises FileNotFoundError for a missing version."""
        with TemporaryDirectory() as tmp:
            recipes_dir = Path(tmp) / "recipes"
            recipes_dir.mkdir()

            backend = LocalBackend(recipes_dir=recipes_dir)
            with self.assertRaises(FileNotFoundError):
                backend.fetch_recipe("nope", "1.0.0", Path(tmp) / "dest")


class TestLocalBackendEntrypoint(unittest.TestCase):
    """Tests for LocalBackend.entrypoint property."""

    def test_default_entrypoint(self) -> None:
        """Default entrypoint is 'nskit.recipes'."""
        backend = LocalBackend(recipes_dir=Path("."))
        self.assertEqual(backend.entrypoint, "nskit.recipes")

    def test_custom_entrypoint(self) -> None:
        """Custom entrypoint is returned."""
        backend = LocalBackend(recipes_dir=Path("."), entrypoint="custom.entry")
        self.assertEqual(backend.entrypoint, "custom.entry")


if __name__ == "__main__":
    unittest.main()
