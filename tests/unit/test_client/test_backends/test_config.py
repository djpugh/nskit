"""Tests for backend configuration factory."""

import os
import tempfile
import unittest
from pathlib import Path

from nskit.client.backends import LocalBackend
from nskit.client.backends.config import create_backend_from_config
from nskit.client.backends.docker import DockerBackend
from nskit.client.backends.github import GitHubBackend


class TestCreateBackendFromConfig(unittest.TestCase):
    """Tests for create_backend_from_config."""

    def test_local_from_dict(self):
        """Create LocalBackend from dict config."""
        result = create_backend_from_config({"type": "local", "path": "/tmp"})
        self.assertIsInstance(result, LocalBackend)

    def test_docker_from_dict(self):
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("type: local\npath: /tmp\n")
            f.flush()
            try:
                result = create_backend_from_config(f.name)
                self.assertIsInstance(result, LocalBackend)
            finally:
                os.unlink(f.name)

    def test_from_path_object(self):
        """Create backend from Path object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("type: local\npath: /tmp\n")
            f.flush()
            try:
                result = create_backend_from_config(Path(f.name))
                self.assertIsInstance(result, LocalBackend)
            finally:
                os.unlink(f.name)

    def test_unknown_type_raises(self):
        """Unknown backend type raises ValueError."""
        with self.assertRaises(ValueError, msg="Unknown backend type"):
            create_backend_from_config({"type": "unknown"})

    def test_default_type_is_local(self):
        """Missing type defaults to local."""
        result = create_backend_from_config({"path": "/tmp"})
        self.assertIsInstance(result, LocalBackend)


if __name__ == "__main__":
    unittest.main()
