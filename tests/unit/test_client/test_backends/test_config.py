"""Tests for backend configuration factory."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from nskit.client.backends import LocalBackend
from nskit.client.backends.config import create_backend_from_config
from nskit.client.backends.docker import DockerBackend
from nskit.client.backends.github import GitHubBackend


class TestCreateBackendFromConfig(unittest.TestCase):
    """Tests for create_backend_from_config."""

    def test_local_from_dict(self):
        """Create LocalBackend from dict config."""
        result = create_backend_from_config({"type": "local", "recipes_dir": "/tmp"})
        self.assertIsInstance(result, LocalBackend)

    @patch("nskit.client.backends.docker.DockerBackend._check_docker")
    def test_docker_from_dict(self, _mock_check):
        """Create DockerBackend from dict config."""
        result = create_backend_from_config(
            {
                "type": "docker",
                "registry_url": "ghcr.io",
                "image_prefix": "org/project",
            }
        )
        self.assertIsInstance(result, DockerBackend)

    def test_github_from_dict(self):
        """Create GitHubBackend from dict config."""
        result = create_backend_from_config(
            {
                "type": "github",
                "org": "myorg",
            }
        )
        self.assertIsInstance(result, GitHubBackend)

    def test_from_yaml_file(self):
        """Create backend from YAML file path."""
        with TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "backend.yml"
            cfg.write_text("type: local\nrecipes_dir: /tmp\n")
            result = create_backend_from_config(str(cfg))
            self.assertIsInstance(result, LocalBackend)

    def test_from_path_object(self):
        """Create backend from Path object."""
        with TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "backend.yml"
            cfg.write_text("type: local\nrecipes_dir: /tmp\n")
            result = create_backend_from_config(cfg)
            self.assertIsInstance(result, LocalBackend)

    def test_unknown_type_raises(self):
        """Unknown backend type raises ValueError."""
        with self.assertRaises(ValueError):
            create_backend_from_config({"type": "unknown"})

    def test_default_type_is_local(self):
        """Missing type defaults to local."""
        result = create_backend_from_config({"recipes_dir": "/tmp"})
        self.assertIsInstance(result, LocalBackend)


if __name__ == "__main__":
    unittest.main()
