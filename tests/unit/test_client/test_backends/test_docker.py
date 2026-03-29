"""Unit tests for DockerBackend."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from nskit.client.backends.docker import DockerBackend


class TestDockerBackendImageUrl(unittest.TestCase):
    """Tests for DockerBackend._build_image_url."""

    @patch("nskit.client.backends.docker.subprocess")
    def test_image_url_with_prefix(self, mock_subprocess: MagicMock) -> None:
        """Image URL includes registry, prefix, recipe name, and version."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend(
            registry_url="ghcr.io",
            image_prefix="myorg/recipes",
        )
        url = backend._build_image_url("my-recipe", "1.0.0")
        self.assertEqual(url, "ghcr.io/myorg/recipes/my-recipe:1.0.0")

    @patch("nskit.client.backends.docker.subprocess")
    def test_image_url_without_prefix(self, mock_subprocess: MagicMock) -> None:
        """Image URL omits prefix when not configured."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend(registry_url="ghcr.io", image_prefix="")
        url = backend._build_image_url("recipe", "2.0.0")
        self.assertEqual(url, "ghcr.io/recipe:2.0.0")


class TestDockerBackendGetImageUrl(unittest.TestCase):
    """Tests for DockerBackend.get_image_url."""

    @patch("nskit.client.backends.docker.subprocess")
    def test_get_image_url(self, mock_subprocess: MagicMock) -> None:
        """get_image_url delegates to _build_image_url."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend(
            registry_url="ghcr.io",
            image_prefix="org",
        )
        url = backend.get_image_url("recipe", "1.0.0")
        self.assertEqual(url, "ghcr.io/org/recipe:1.0.0")


class TestDockerBackendListRecipes(unittest.TestCase):
    """Tests for DockerBackend.list_recipes."""

    @patch("nskit.client.backends.docker.subprocess")
    def test_returns_empty_list(self, mock_subprocess: MagicMock) -> None:
        """Docker backend cannot list recipes (registry limitation)."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend()
        self.assertEqual(backend.list_recipes(), [])


class TestDockerBackendEntrypoint(unittest.TestCase):
    """Tests for DockerBackend.entrypoint property."""

    @patch("nskit.client.backends.docker.subprocess")
    def test_default_entrypoint(self, mock_subprocess: MagicMock) -> None:
        """Default entrypoint is 'nskit.recipes'."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend()
        self.assertEqual(backend.entrypoint, "nskit.recipes")

    @patch("nskit.client.backends.docker.subprocess")
    def test_custom_entrypoint(self, mock_subprocess: MagicMock) -> None:
        """Custom entrypoint is returned."""
        mock_subprocess.run.return_value = MagicMock(returncode=0)
        backend = DockerBackend(entrypoint="custom.ep")
        self.assertEqual(backend.entrypoint, "custom.ep")


class TestDockerBackendCheckDocker(unittest.TestCase):
    """Tests for DockerBackend._check_docker."""

    @patch("nskit.client.backends.docker.subprocess")
    def test_raises_when_docker_not_found(
        self,
        mock_subprocess: MagicMock,
    ) -> None:
        """Raises RuntimeError when docker binary is missing."""
        mock_subprocess.run.side_effect = FileNotFoundError
        with self.assertRaises(RuntimeError) as ctx:
            DockerBackend()
        self.assertIn("not found", str(ctx.exception).lower())

    @patch("nskit.client.backends.docker.subprocess")
    def test_raises_when_docker_not_running(
        self,
        mock_subprocess: MagicMock,
    ) -> None:
        """Raises RuntimeError when docker daemon is not running."""
        import subprocess as real_subprocess

        mock_subprocess.run.side_effect = real_subprocess.CalledProcessError(
            1,
            "docker info",
        )
        mock_subprocess.CalledProcessError = real_subprocess.CalledProcessError
        mock_subprocess.TimeoutExpired = real_subprocess.TimeoutExpired
        with self.assertRaises(RuntimeError) as ctx:
            DockerBackend()
        self.assertIn("not running", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
