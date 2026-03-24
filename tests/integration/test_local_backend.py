"""Tests for LocalBackend."""
import pytest
from pathlib import Path

from nskit.client.backends import LocalBackend


@pytest.fixture
def recipes_dir(tmp_path):
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


class TestLocalBackend:
    """Test LocalBackend."""

    def test_entrypoint(self, recipes_dir):
        """Test entrypoint property."""
        backend = LocalBackend(recipes_dir=recipes_dir, entrypoint="custom.recipes")
        assert backend.entrypoint == "custom.recipes"

    def test_entrypoint_default(self, recipes_dir):
        """Test default entrypoint."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        assert backend.entrypoint == "nskit.recipes"

    def test_list_recipes(self, recipes_dir):
        """Test listing recipes from directory."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        recipes = backend.list_recipes()

        names = {r.name for r in recipes}
        assert names == {"recipe_a", "recipe_b"}
        assert ".hidden" not in names

    def test_list_recipes_versions(self, recipes_dir):
        """Test that listed recipes include correct versions."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        recipes = backend.list_recipes()

        recipe_a = next(r for r in recipes if r.name == "recipe_a")
        assert recipe_a.versions == ["v1.0.0", "v2.0.0"]

        recipe_b = next(r for r in recipes if r.name == "recipe_b")
        assert recipe_b.versions == ["v1.0.0"]

    def test_list_recipes_empty_dir(self, tmp_path):
        """Test listing recipes from empty directory."""
        backend = LocalBackend(recipes_dir=tmp_path)
        assert backend.list_recipes() == []

    def test_list_recipes_nonexistent_dir(self, tmp_path):
        """Test listing recipes from nonexistent directory."""
        backend = LocalBackend(recipes_dir=tmp_path / "nonexistent")
        assert backend.list_recipes() == []

    def test_get_recipe_versions(self, recipes_dir):
        """Test getting versions for a recipe."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        versions = backend.get_recipe_versions("recipe_a")
        assert versions == ["v1.0.0", "v2.0.0"]

    def test_get_recipe_versions_single(self, recipes_dir):
        """Test getting versions for recipe with one version."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        versions = backend.get_recipe_versions("recipe_b")
        assert versions == ["v1.0.0"]

    def test_get_recipe_versions_nonexistent(self, recipes_dir):
        """Test getting versions for nonexistent recipe."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        assert backend.get_recipe_versions("nonexistent") == []

    def test_fetch_recipe(self, recipes_dir, tmp_path):
        """Test fetching recipe copies files."""
        backend = LocalBackend(recipes_dir=recipes_dir)
        dest = tmp_path / "dest"

        result = backend.fetch_recipe("recipe_a", "v1.0.0", dest)

        assert result == dest / "recipe_a"
        assert (result / "README.md").read_text() == "# Recipe A v1"
        assert (result / "config.txt").read_text() == "key=value"

    def test_fetch_recipe_nonexistent_version(self, recipes_dir, tmp_path):
        """Test fetching nonexistent version raises error."""
        backend = LocalBackend(recipes_dir=recipes_dir)

        with pytest.raises(FileNotFoundError):
            backend.fetch_recipe("recipe_a", "v9.9.9", tmp_path / "dest")

    def test_fetch_recipe_nonexistent_recipe(self, recipes_dir, tmp_path):
        """Test fetching nonexistent recipe raises error."""
        backend = LocalBackend(recipes_dir=recipes_dir)

        with pytest.raises(FileNotFoundError):
            backend.fetch_recipe("nonexistent", "v1.0.0", tmp_path / "dest")
