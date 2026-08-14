"""Tests for recipe execution engines."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.models import RecipeResult


class TestDockerEngine(unittest.TestCase):
    """Test DockerEngine directly."""

    def test_requires_image_url(self):
        """Execute raises ValueError without image_url."""
        engine = DockerEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            with self.assertRaisesRegex(ValueError, "image_url"):
                engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=Path(tmp_path),
                    image_url=None,
                )

    def test_success_returns_result(self):
        """Successful execution returns RecipeResult with success=True."""
        engine = DockerEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            output = Path(tmp_path) / "output"
            output.mkdir()
            (output / "file.txt").write_text("x")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                result = engine.execute(
                    recipe="my-recipe",
                    version="v1.0.0",
                    parameters={"name": "test"},
                    output_dir=output,
                    image_url="ghcr.io/test:v1",
                )

            self.assertTrue(result.success)
            self.assertEqual(result.recipe_name, "my-recipe")
            self.assertEqual(result.recipe_version, "v1.0.0")
            self.assertIn(Path("file.txt"), result.files_created)

    def test_subprocess_failure_returns_error(self):
        """Subprocess failure returns RecipeResult with success=False."""
        engine = DockerEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            with patch("subprocess.run", side_effect=Exception("docker not found")):
                result = engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=Path(tmp_path),
                    image_url="img:latest",
                )

            self.assertFalse(result.success)
            self.assertTrue(any("docker not found" in e for e in result.errors))

    def test_command_structure(self):
        """Docker run command has correct structure."""
        engine = DockerEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            output = Path(tmp_path) / "output"
            output.mkdir()

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=output,
                    image_url="img:v1",
                )

            # pull call, then run call (+ optional chown on Linux)
            self.assertGreaterEqual(mock_run.call_count, 2)
            pull_cmd = mock_run.call_args_list[0][0][0]
            self.assertEqual(pull_cmd, ["docker", "pull", "img:v1"])

            run_cmd = mock_run.call_args_list[1][0][0]
            self.assertEqual(run_cmd[0:2], ["docker", "run"])
            self.assertIn("--rm", run_cmd)
            self.assertIn("img:v1", run_cmd)


class TestLocalEngine(unittest.TestCase):
    """Test LocalEngine directly."""

    def test_requires_entrypoint(self):
        """Execute raises ValueError without entrypoint."""
        engine = LocalEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            with self.assertRaisesRegex(ValueError, "entrypoint"):
                engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=Path(tmp_path),
                    entrypoint=None,
                )

    def test_success_returns_result(self):
        """Successful execution returns RecipeResult with files."""
        engine = LocalEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            output = Path(tmp_path) / "output"

            with patch("nskit.client.engines.local.Recipe") as MockRecipe:
                mock_instance = Mock()
                mock_instance.create.return_value = {"README.md": "content", "setup.py": "content"}
                MockRecipe.load.return_value = mock_instance

                result = engine.execute(
                    recipe="my-recipe",
                    version="v1.0.0",
                    parameters={"name": "test"},
                    output_dir=output,
                    entrypoint="test.recipes",
                )

            self.assertTrue(result.success)
            self.assertEqual(result.recipe_name, "my-recipe")
            self.assertEqual(set(result.files_created), {Path("README.md"), Path("setup.py")})
            MockRecipe.load.assert_called_once_with("my-recipe", entrypoint="test.recipes", name="test")

    def test_recipe_load_failure_returns_error(self):
        """Recipe load failure returns RecipeResult with success=False."""
        engine = LocalEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            with patch("nskit.client.engines.local.Recipe") as MockRecipe:
                MockRecipe.load.side_effect = ModuleNotFoundError("No module named 'fake'")

                result = engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=Path(tmp_path),
                    entrypoint="fake.recipes",
                )

            self.assertFalse(result.success)
            self.assertTrue(any("fake" in e for e in result.errors))

    def test_recipe_create_failure_returns_error(self):
        """Recipe create failure returns RecipeResult with success=False."""
        engine = LocalEngine()
        with tempfile.TemporaryDirectory() as tmp_path:
            with patch("nskit.client.engines.local.Recipe") as MockRecipe:
                mock_instance = Mock()
                mock_instance.create.side_effect = RuntimeError("disk full")
                MockRecipe.load.return_value = mock_instance

                result = engine.execute(
                    recipe="r",
                    version="v1",
                    parameters={},
                    output_dir=Path(tmp_path),
                    entrypoint="test.recipes",
                )

            self.assertFalse(result.success)
            self.assertTrue(any("disk full" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
