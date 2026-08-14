"""Tests for LocalBackend."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from nskit.client.backends import LocalBackend


class TestLocalBackend(unittest.TestCase):
    """Test LocalBackend."""

    def _create_recipes_dir(self, tmp_path):
        """Create a recipes directory with test data."""
        # recipe_a with 2 versions
        (tmp_path / "recipe_a" / "v1.0.0").mkdir(parents=True)
        (tmp_path / "recipe_a" / "v1.0.0" / "README.md").write_text("# Recipe A v1")
        (tmp_path / "recipe_a" / "v1.0.0" / "config.txt").write_text("key=value")
        (tmp_path / "recipe_a" / "v2.0.0").mkdir(parents=True)
        (tmp_path / "recipe_a" / "v2.0.0" / "README.md").write_text("# Recipe A v2")

        # recipe_b with 1 version
        (tmp_path / "recipe_b" / "v1.0.0").mkdir(parents=True)
        (tmp_path / "recipe_b" / "v1.0.0" / "main.py").write_text("print('hello')")

        # hidden dir (should be ignored)
        (tmp_path / ".hidden").mkdir()

        return tmp_path

    def test_entrypoint(self):
        """Test entrypoint property."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir, entrypoint="custom.recipes")
            self.assertEqual(backend.entrypoint, "custom.recipes")

    def test_entrypoint_default(self):
        """Test default entrypoint."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            self.assertEqual(backend.entrypoint, "nskit.recipes")

    def test_list_recipes(self):
        """Test listing recipes from directory."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            recipes = backend.list_recipes()

            names = {r.name for r in recipes}
            self.assertEqual(names, {"recipe_a", "recipe_b"})
            self.assertNotIn(".hidden", names)

    def test_list_recipes_versions(self):
        """Test that listed recipes include correct versions."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            recipes = backend.list_recipes()

            recipe_a = next(r for r in recipes if r.name == "recipe_a")
            self.assertEqual(recipe_a.versions, ["v1.0.0", "v2.0.0"])

            recipe_b = next(r for r in recipes if r.name == "recipe_b")
            self.assertEqual(recipe_b.versions, ["v1.0.0"])

    def test_list_recipes_empty_dir(self):
        """Test listing recipes from empty directory."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            backend = LocalBackend(recipes_dir=tmp_path)
            self.assertEqual(backend.list_recipes(), [])

    def test_list_recipes_nonexistent_dir(self):
        """Test listing recipes from nonexistent directory."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            backend = LocalBackend(recipes_dir=tmp_path / "nonexistent")
            self.assertEqual(backend.list_recipes(), [])

    def test_get_recipe_versions(self):
        """Test getting versions for a recipe."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            versions = backend.get_recipe_versions("recipe_a")
            self.assertEqual(versions, ["v1.0.0", "v2.0.0"])

    def test_get_recipe_versions_single(self):
        """Test getting versions for recipe with one version."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            versions = backend.get_recipe_versions("recipe_b")
            self.assertEqual(versions, ["v1.0.0"])

    def test_get_recipe_versions_nonexistent(self):
        """Test getting versions for nonexistent recipe."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            self.assertEqual(backend.get_recipe_versions("nonexistent"), [])

    def test_fetch_recipe(self):
        """Test fetching recipe copies files."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)
            dest = tmp_path / "dest"

            result = backend.fetch_recipe("recipe_a", "v1.0.0", dest)

            self.assertEqual(result, dest / "recipe_a")
            self.assertEqual((result / "README.md").read_text(), "# Recipe A v1")
            self.assertEqual((result / "config.txt").read_text(), "key=value")

    def test_fetch_recipe_nonexistent_version(self):
        """Test fetching nonexistent version raises error."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)

            with self.assertRaises(FileNotFoundError):
                backend.fetch_recipe("recipe_a", "v9.9.9", tmp_path / "dest")

    def test_fetch_recipe_nonexistent_recipe(self):
        """Test fetching nonexistent recipe raises error."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            recipes_dir = self._create_recipes_dir(tmp_path)
            backend = LocalBackend(recipes_dir=recipes_dir)

            with self.assertRaises(FileNotFoundError):
                backend.fetch_recipe("nonexistent", "v1.0.0", tmp_path / "dest")


if __name__ == "__main__":
    unittest.main()
