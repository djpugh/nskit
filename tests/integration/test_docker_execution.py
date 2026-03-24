"""Tests for Docker execution mode."""
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from nskit.client.recipes import RecipeClient
from nskit.client.engines import DockerEngine, LocalEngine


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
            
            result = client.initialize_recipe(
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
            
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test", "version": "1.0"},
                output_dir=tmp_path / "output",
            )
        
        # Verify docker run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "docker"
        assert call_args[1] == "run"
        assert "--rm" in call_args
        assert "ghcr.io/test/recipe:v1.0.0" in call_args

    def test_docker_mode_mounts_volumes(self, mock_backend, tmp_path):
        """Test that Docker mode mounts output directory."""
        client = RecipeClient(mock_backend, engine=DockerEngine())
        output_dir = tmp_path / "output"
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={},
                output_dir=output_dir,
            )
        
        # Verify volume mount
        call_args = mock_run.call_args[0][0]
        assert "-v" in call_args
        # Find the output volume mount
        v_index = [i for i, arg in enumerate(call_args) if arg == "-v"]
        assert any(f"{output_dir.absolute()}:/app/output" in call_args[i+1] for i in v_index)

    def test_docker_mode_passes_parameters(self, mock_backend, tmp_path):
        """Test that Docker mode passes parameters via JSON file."""
        client = RecipeClient(mock_backend, engine=DockerEngine())
        params = {"name": "test-project", "version": "1.0", "author": "Test"}
        
        with patch("subprocess.run") as mock_run, \
             patch("tempfile.NamedTemporaryFile") as mock_temp:
            
            mock_file = MagicMock()
            mock_file.name = "/tmp/test.json"
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters=params,
                output_dir=tmp_path / "output",
            )
        
        # Verify JSON was written
        assert mock_file.write.called or mock_temp.called

    def test_local_mode_uses_installed_package(self, mock_backend, tmp_path):
        """Test that local mode uses installed package."""
        client = RecipeClient(mock_backend, engine=LocalEngine())
        
        with patch("nskit.mixer.components.Recipe.load") as mock_load:
            mock_recipe = Mock()
            mock_recipe.create = Mock(return_value={"file1.txt": "content"})
            mock_load.return_value = mock_recipe
            
            result = client.initialize_recipe(
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
