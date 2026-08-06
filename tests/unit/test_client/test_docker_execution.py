"""Tests for Docker execution mode."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.recipes import RecipeClient


class TestDockerExecution:
    """Test Docker execution pathway."""

    @pytest.fixture
    def mock_backend(self):
        """Create mock backend."""
        backend = Mock()
        backend.entrypoint = "test.recipes"
        backend.get_image_url = Mock(return_value="ghcr.io/test/recipe:v1.0.0")
        backend.pull_image = Mock()
        return backend

    def test_docker_mode_pulls_image(self, mock_backend, tmp_path):
        """Test that Docker mode pulls image."""
        client = RecipeClient(mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=tmp_path / "output",
            )

        # Verify image was pulled
        mock_backend.get_image_url.assert_called_once_with("test-recipe", "v1.0.0")
        mock_backend.pull_image.assert_called_once_with("ghcr.io/test/recipe:v1.0.0")

    def test_docker_mode_runs_container(self, mock_backend, tmp_path):
        """Test that Docker mode runs container with correct arguments."""
        client = RecipeClient(mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test", "version": "1.0"},
                output_dir=tmp_path / "output",
            )

        # Verify docker run was called (find the init call, not the chown)
        assert mock_run.called
        run_calls = [
            c[0][0] for c in mock_run.call_args_list if c[0][0][0:2] == ["docker", "run"] and "init" in c[0][0]
        ]
        assert len(run_calls) == 1
        call_args = run_calls[0]
        assert "--rm" in call_args
        assert "ghcr.io/test/recipe:v1.0.0" in call_args

    def test_docker_mode_mounts_volumes(self, mock_backend, tmp_path):
        """Test that Docker mode mounts output directory."""
        client = RecipeClient(mock_backend, engine=DockerEngine())
        output_dir = tmp_path / "output"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={},
                output_dir=output_dir,
            )

        # Verify volume mount (find the init call, not the chown)
        run_calls = [
            c[0][0] for c in mock_run.call_args_list if c[0][0][0:2] == ["docker", "run"] and "init" in c[0][0]
        ]
        assert len(run_calls) == 1
        call_args = run_calls[0]
        assert "-v" in call_args
        # Find the output volume mount
        v_index = [i for i, arg in enumerate(call_args) if arg == "-v"]
        assert any(f"{output_dir.absolute()}:/app/output" in call_args[i + 1] for i in v_index)

    def test_docker_mode_passes_parameters(self, mock_backend, tmp_path):
        """Docker mode writes parameters to a YAML file and mounts it as input.

        Asserts on the mount and contents rather than the tempfile API, so the
        staging location is an implementation detail.
        """
        import yaml

        client = RecipeClient(mock_backend, engine=DockerEngine())
        params = {"name": "test-project", "version": "1.0", "author": "Test"}
        staged: dict[str, object] = {}

        def capture(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "run" in cmd:
                mount = next((a for a in cmd if a.endswith(":/app/input.yml:ro")), None)
                if mount:
                    host_path = Path(mount.split(":/app/input.yml:ro")[0])
                    staged["path"] = host_path
                    staged["contents"] = yaml.safe_load(host_path.read_text())
                    # Simulate recipe output so the engine reports success.
                    output_dir = tmp_path / "output"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    (output_dir / "generated.txt").write_text("x")
            return Mock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=capture):
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters=params,
                output_dir=tmp_path / "output",
            )

        assert result.success, result.errors
        assert staged["contents"] == params
        # Staging dir cleaned up after the run.
        assert not staged["path"].exists()

    def test_input_not_staged_inside_output_directory(self, mock_backend, tmp_path):
        """The input file must not land inside the generated project.

        Recipe post-hooks (git init) run against the output directory, and
        parameters may contain secrets.
        """
        client = RecipeClient(mock_backend, engine=DockerEngine())
        output_dir = tmp_path / "output"
        seen: list[Path] = []

        def capture(cmd, *args, **kwargs):
            if isinstance(cmd, list) and "run" in cmd:
                mount = next((a for a in cmd if a.endswith(":/app/input.yml:ro")), None)
                if mount:
                    seen.append(Path(mount.split(":/app/input.yml:ro")[0]))
                    output_dir.mkdir(parents=True, exist_ok=True)
                    (output_dir / "generated.txt").write_text("x")
            return Mock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=capture):
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=output_dir,
            )

        assert result.success, result.errors
        assert output_dir not in seen[0].parents

    def test_no_files_produced_is_reported_as_error(self, mock_backend, tmp_path):
        """A clean exit producing nothing must fail, not silently succeed.

        Docker creates an empty directory at the mount target when the host path
        is unshared, so the recipe runs inside the container but the host sees
        nothing.
        """
        client = RecipeClient(mock_backend, engine=DockerEngine())

        with patch("subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")):
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=tmp_path / "output",
            )

        assert not result.success
        assert any("produced no files" in e for e in result.errors)

    def test_local_mode_uses_installed_package(self, mock_backend, tmp_path):
        """Test that local mode uses installed package."""
        client = RecipeClient(mock_backend, engine=LocalEngine())

        with patch("nskit.mixer.components.Recipe.load") as mock_load:
            mock_recipe = Mock()
            mock_recipe.create = Mock(return_value={"file1.txt": "content"})
            mock_load.return_value = mock_recipe

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=tmp_path / "output",
            )

        # Verify Recipe.load was called
        mock_load.assert_called_once()
        mock_recipe.create.assert_called_once()

        # Verify backend methods were NOT called
        mock_backend.get_image_url.assert_not_called()
        mock_backend.pull_image.assert_not_called()

    def test_execution_mode_can_be_changed(self, mock_backend, tmp_path):
        """Test that engine can be changed after initialization."""
        client = RecipeClient(mock_backend, engine=DockerEngine())
        assert isinstance(client.engine, DockerEngine)

        client.engine = LocalEngine()
        assert isinstance(client.engine, LocalEngine)

    def test_docker_mode_handles_container_failure(self, mock_backend, tmp_path):
        """Test that Docker mode handles container execution failures."""
        client = RecipeClient(mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Container failed")

            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={},
                output_dir=tmp_path / "output",
            )

        assert not result.success
        assert len(result.errors) > 0
        assert "Container failed" in result.errors[0]


class TestEngines:
    """Test execution engines."""

    def test_docker_engine_exists(self):
        """Test DockerEngine class exists."""
        assert DockerEngine is not None

    def test_local_engine_exists(self):
        """Test LocalEngine class exists."""
        assert LocalEngine is not None
