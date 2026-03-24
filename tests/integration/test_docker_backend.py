"""Tests for Docker backend."""
import pytest
import subprocess
from unittest.mock import patch, Mock

from nskit.client.backends import DockerBackend


class TestDockerBackend:
    """Test DockerBackend."""

    def test_initialization_success(self):
        """Test successful initialization when Docker is running."""
        with patch('nskit.client.backends.docker.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            backend = DockerBackend(registry_url="ghcr.io", image_prefix="org/project")
            
            assert backend.registry_url == "ghcr.io"
            assert backend.image_prefix == "org/project"
            mock_run.assert_called_once()

    def test_docker_not_installed(self):
        """Test error when Docker not installed."""
        with patch('nskit.client.backends.docker.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            with pytest.raises(RuntimeError, match="install Docker"):
                DockerBackend()

    def test_docker_not_running(self):
        """Test error when Docker not running."""
        with patch('nskit.client.backends.docker.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
            
            with pytest.raises(RuntimeError, match="not running"):
                DockerBackend()

    def test_docker_not_responding(self):
        """Test error when Docker not responding."""
        with patch('nskit.client.backends.docker.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)
            
            with pytest.raises(RuntimeError, match="not responding"):
                DockerBackend()

    def test_build_image_url_with_prefix(self):
        """Test building image URL with prefix."""
        with patch('nskit.client.backends.docker.subprocess.run'):
            backend = DockerBackend(
                registry_url="ghcr.io",
                image_prefix="myorg/myproject"
            )
            
            url = backend._build_image_url("python_package", "v1.0.0")
            assert url == "ghcr.io/myorg/myproject/python_package:v1.0.0"

    def test_build_image_url_without_prefix(self):
        """Test building image URL without prefix."""
        with patch('nskit.client.backends.docker.subprocess.run'):
            backend = DockerBackend(registry_url="ghcr.io")
            
            url = backend._build_image_url("python_package", "v1.0.0")
            assert url == "ghcr.io/python_package:v1.0.0"
