"""Tests for recipe execution engines."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.models import RecipeResult


class TestDockerEngine:
    """Test DockerEngine directly."""

    def test_requires_image_url(self, tmp_path):
        """Execute raises ValueError without image_url."""
        engine = DockerEngine()
        with pytest.raises(ValueError, match="image_url"):
            engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=tmp_path, image_url=None,
            )

    def test_success_returns_result(self, tmp_path):
        """Successful execution returns RecipeResult with success=True."""
        engine = DockerEngine()
        output = tmp_path / "output"
        output.mkdir()
        (output / "file.txt").write_text("x")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = engine.execute(
                recipe="my-recipe", version="v1.0.0",
                parameters={"name": "test"}, output_dir=output,
                image_url="ghcr.io/test:v1",
            )

        assert result.success
        assert result.recipe_name == "my-recipe"
        assert result.recipe_version == "v1.0.0"
        assert Path("file.txt") in result.files_created

    def test_subprocess_failure_returns_error(self, tmp_path):
        """Subprocess failure returns RecipeResult with success=False."""
        engine = DockerEngine()
        with patch("subprocess.run", side_effect=Exception("docker not found")):
            result = engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=tmp_path, image_url="img:latest",
            )

        assert not result.success
        assert any("docker not found" in e for e in result.errors)

    def test_command_structure(self, tmp_path):
        """Docker run command has correct structure."""
        engine = DockerEngine()
        output = tmp_path / "output"
        output.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=output, image_url="img:v1",
            )

        # pull call, then run call
        assert mock_run.call_count == 2
        pull_cmd = mock_run.call_args_list[0][0][0]
        assert pull_cmd == ["docker", "pull", "img:v1"]

        run_cmd = mock_run.call_args_list[1][0][0]
        assert run_cmd[0:2] == ["docker", "run"]
        assert "--rm" in run_cmd
        assert "img:v1" in run_cmd


class TestLocalEngine:
    """Test LocalEngine directly."""

    def test_requires_entrypoint(self, tmp_path):
        """Execute raises ValueError without entrypoint."""
        engine = LocalEngine()
        with pytest.raises(ValueError, match="entrypoint"):
            engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=tmp_path, entrypoint=None,
            )

    def test_success_returns_result(self, tmp_path):
        """Successful execution returns RecipeResult with files."""
        engine = LocalEngine()
        output = tmp_path / "output"

        with patch("nskit.mixer.components.Recipe") as MockRecipe:
            mock_instance = Mock()
            mock_instance.create.return_value = {"README.md": "content", "setup.py": "content"}
            MockRecipe.load.return_value = mock_instance

            result = engine.execute(
                recipe="my-recipe", version="v1.0.0",
                parameters={"name": "test"}, output_dir=output,
                entrypoint="test.recipes",
            )

        assert result.success
        assert result.recipe_name == "my-recipe"
        assert set(result.files_created) == {Path("README.md"), Path("setup.py")}
        MockRecipe.load.assert_called_once_with("my-recipe", entrypoint="test.recipes", name="test")

    def test_recipe_load_failure_returns_error(self, tmp_path):
        """Recipe load failure returns RecipeResult with success=False."""
        engine = LocalEngine()

        with patch("nskit.mixer.components.Recipe") as MockRecipe:
            MockRecipe.load.side_effect = ModuleNotFoundError("No module named 'fake'")

            result = engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=tmp_path, entrypoint="fake.recipes",
            )

        assert not result.success
        assert any("fake" in e for e in result.errors)

    def test_recipe_create_failure_returns_error(self, tmp_path):
        """Recipe create failure returns RecipeResult with success=False."""
        engine = LocalEngine()

        with patch("nskit.mixer.components.Recipe") as MockRecipe:
            mock_instance = Mock()
            mock_instance.create.side_effect = RuntimeError("disk full")
            MockRecipe.load.return_value = mock_instance

            result = engine.execute(
                recipe="r", version="v1", parameters={},
                output_dir=tmp_path, entrypoint="test.recipes",
            )

        assert not result.success
        assert any("disk full" in e for e in result.errors)
