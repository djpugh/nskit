"""Unit tests for InitManager."""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import yaml

from nskit.client.exceptions import InitError
from nskit.client.init import InitManager
from nskit.client.models import RecipeInfo, RecipeResult


class TestInitManagerFileBased(unittest.TestCase):
    """Tests for InitManager with file-based (non-interactive) input."""

    def _make_backend_and_engine(self) -> tuple[MagicMock, MagicMock]:
        """Create mock backend and engine."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0"]
        backend.get_image_url.return_value = "ghcr.io/org/recipe:1.0.0"
        engine = MagicMock()
        return backend, engine

    def test_file_based_init_success(self) -> None:
        """Successful initialisation from a YAML input file."""
        backend, engine = self._make_backend_and_engine()

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "project"
            output_dir.mkdir()

            # Write input YAML
            input_yaml = tmp_path / "input.yml"
            input_yaml.write_text(
                yaml.dump({"project_name": "test", "author": "dev"}),
                encoding="utf-8",
            )

            # Mock engine execution
            engine.execute.return_value = RecipeResult(
                success=True,
                project_path=output_dir,
                recipe_name="my-recipe",
                recipe_version="1.0.0",
            )

            mgr = InitManager(backend, engine)
            result = mgr.initialize(
                recipe_name="my-recipe",
                input_yaml_path=input_yaml,
                output_dir=output_dir,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.recipe_name, "my-recipe")

    def test_missing_yaml_raises_init_error(self) -> None:
        """Raises InitError when the input YAML file does not exist."""
        backend, engine = self._make_backend_and_engine()
        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent.yml"
            with self.assertRaises(InitError):
                mgr.initialize(
                    recipe_name="recipe",
                    input_yaml_path=missing,
                    output_dir=Path(tmp) / "out",
                )

    def test_invalid_yaml_raises_init_error(self) -> None:
        """Raises InitError when the YAML file contains invalid content."""
        backend, engine = self._make_backend_and_engine()
        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            bad_yaml = Path(tmp) / "bad.yml"
            bad_yaml.write_text("- just a list", encoding="utf-8")

            with self.assertRaises(InitError):
                mgr.initialize(
                    recipe_name="recipe",
                    input_yaml_path=bad_yaml,
                    output_dir=Path(tmp) / "out",
                )


class TestInitManagerInteractive(unittest.TestCase):
    """Tests for InitManager with interactive handler."""

    def test_cancellation_raises_init_error(self) -> None:
        """Raises InitError when user cancels confirmation."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0"]
        engine = MagicMock()

        handler = MagicMock()
        handler.confirm_initialisation.return_value = False

        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            with self.assertRaises(InitError) as ctx:
                mgr.initialize(
                    recipe_name="recipe",
                    output_dir=Path(tmp),
                    interactive_handler=handler,
                )
            self.assertIn("cancelled", str(ctx.exception).lower())

    def test_no_recipe_name_and_no_handler_raises(self) -> None:
        """Raises InitError when no recipe name and no handler provided."""
        backend = MagicMock()
        engine = MagicMock()
        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            with self.assertRaises(InitError):
                mgr.initialize(output_dir=Path(tmp))

    def test_no_recipes_available_raises(self) -> None:
        """Raises InitError when backend has no recipes."""
        backend = MagicMock()
        backend.list_recipes.return_value = []
        engine = MagicMock()
        handler = MagicMock()

        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            with self.assertRaises(InitError):
                mgr.initialize(
                    output_dir=Path(tmp),
                    interactive_handler=handler,
                )

    def test_recipe_selection_cancelled_raises(self) -> None:
        """Raises InitError when user cancels recipe selection."""
        backend = MagicMock()
        backend.list_recipes.return_value = [
            RecipeInfo(name="r1", versions=["1.0.0"]),
        ]
        engine = MagicMock()
        handler = MagicMock()
        handler.select_recipe.return_value = None

        mgr = InitManager(backend, engine)

        with TemporaryDirectory() as tmp:
            with self.assertRaises(InitError):
                mgr.initialize(
                    output_dir=Path(tmp),
                    interactive_handler=handler,
                )


class TestInitManagerRecipeFailure(unittest.TestCase):
    """Tests for InitManager when recipe execution fails."""

    def test_failed_execution_raises_init_error(self) -> None:
        """Raises InitError when the recipe engine reports failure."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0"]
        backend.get_image_url.return_value = "img:1.0.0"
        engine = MagicMock()

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_yaml = tmp_path / "input.yml"
            input_yaml.write_text(yaml.dump({"key": "val"}), encoding="utf-8")

            engine.execute.return_value = RecipeResult(
                success=False,
                project_path=tmp_path / "out",
                recipe_name="recipe",
                recipe_version="1.0.0",
                errors=["Docker pull failed"],
            )

            mgr = InitManager(backend, engine)
            with self.assertRaises(InitError):
                mgr.initialize(
                    recipe_name="recipe",
                    input_yaml_path=input_yaml,
                    output_dir=tmp_path / "out",
                )


class TestInitManagerConfigPersistence(unittest.TestCase):
    """Tests for config persistence after successful init."""

    def test_config_persisted_after_success(self) -> None:
        """Recipe config is written to disk after successful init."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0"]
        backend.get_image_url.return_value = "ghcr.io/org/recipe:1.0.0"
        engine = MagicMock()

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "project"
            output_dir.mkdir()

            input_yaml = tmp_path / "input.yml"
            input_yaml.write_text(
                yaml.dump({"name": "test"}),
                encoding="utf-8",
            )

            engine.execute.return_value = RecipeResult(
                success=True,
                project_path=output_dir,
                recipe_name="my-recipe",
                recipe_version="1.0.0",
            )

            mgr = InitManager(backend, engine)
            mgr.initialize(
                recipe_name="my-recipe",
                input_yaml_path=input_yaml,
                output_dir=output_dir,
            )

            config_path = output_dir / ".recipe" / "config.yml"
            self.assertTrue(config_path.exists())

            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["metadata"]["recipe_name"], "my-recipe")


if __name__ == "__main__":
    unittest.main()
