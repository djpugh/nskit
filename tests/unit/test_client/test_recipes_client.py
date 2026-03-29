"""Unit tests for RecipeClient."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from nskit.client.models import RecipeInfo, RecipeResult
from nskit.client.recipes import RecipeClient


class TestRecipeClientListRecipes(unittest.TestCase):
    """Tests for RecipeClient.list_recipes."""

    def test_delegates_to_backend(self) -> None:
        """list_recipes passes through to the backend."""
        backend = MagicMock()
        expected = [RecipeInfo(name="r1", versions=["1.0.0"])]
        backend.list_recipes.return_value = expected

        client = RecipeClient(backend)
        result = client.list_recipes()

        self.assertEqual(result, expected)
        backend.list_recipes.assert_called_once()


class TestRecipeClientGetRecipeVersions(unittest.TestCase):
    """Tests for RecipeClient.get_recipe_versions."""

    def test_delegates_to_backend(self) -> None:
        """get_recipe_versions passes through to the backend."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0", "2.0.0"]

        client = RecipeClient(backend)
        result = client.get_recipe_versions("my-recipe")

        self.assertEqual(result, ["1.0.0", "2.0.0"])
        backend.get_recipe_versions.assert_called_once_with("my-recipe")


class TestRecipeClientInitializeRecipe(unittest.TestCase):
    """Tests for RecipeClient.initialize_recipe."""

    def test_non_empty_dir_without_force_returns_error(self) -> None:
        """Returns failure when output dir is non-empty and force is False."""
        backend = MagicMock()
        engine = MagicMock()
        client = RecipeClient(backend, engine)

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "existing.txt").write_text("data")

            result = client.initialize_recipe(
                recipe="r",
                version="1.0.0",
                parameters={},
                output_dir=output,
                force=False,
            )

            self.assertFalse(result.success)
            self.assertTrue(len(result.errors) > 0)

    def test_successful_init_delegates_to_engine(self) -> None:
        """Successful init calls engine.execute and returns its result."""
        backend = MagicMock()
        backend.get_image_url.return_value = "ghcr.io/org/r:1.0.0"
        backend.entrypoint = "nskit.recipes"
        engine = MagicMock()
        engine.__class__.__name__ = "DockerEngine"

        expected = RecipeResult(
            success=True,
            project_path=Path("/tmp/out"),
            recipe_name="r",
            recipe_version="1.0.0",
        )
        engine.execute.return_value = expected

        client = RecipeClient(backend, engine)

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "project"
            result = client.initialize_recipe(
                recipe="r",
                version="1.0.0",
                parameters={"name": "test"},
                output_dir=output,
            )

            self.assertTrue(result.success)
            engine.execute.assert_called_once()

    def test_engine_exception_returns_error(self) -> None:
        """Engine exception is caught and returned as error result."""
        backend = MagicMock()
        backend.entrypoint = "nskit.recipes"
        engine = MagicMock()
        engine.__class__.__name__ = "OtherEngine"
        engine.execute.side_effect = RuntimeError("boom")

        client = RecipeClient(backend, engine)

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "project"
            result = client.initialize_recipe(
                recipe="r",
                version="1.0.0",
                parameters={},
                output_dir=output,
            )

            self.assertFalse(result.success)
            self.assertTrue(any("boom" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
