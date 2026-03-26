"""Smoke tests for Docker and Local recipe execution engines.

Verifies that both engine paths produce correct results through
the RecipeClient orchestration layer. The Docker tests build a real
image from the nskit Dockerfile and execute a recipe inside it.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.recipes import RecipeClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NSKIT_ROOT = Path(__file__).resolve().parents[2]  # nskit repo root
DOCKER_IMAGE_TAG = "nskit-smoke-test:latest"


def _docker_available() -> bool:
    """Return True if Docker daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _fix_docker_permissions(path: Path) -> None:
    """Fix root-owned files created by Docker so the host user can delete them."""
    subprocess.run(  # nosec B603, B607
        ["docker", "run", "--rm", "-v", f"{path.absolute()}:/fix", "busybox", "chmod", "-R", "a+rwX", "/fix"],
        capture_output=True,
        timeout=30,
    )


@contextlib.contextmanager
def _docker_tmpdir():
    """Temporary directory that cleans up root-owned Docker output."""
    tmp = tempfile.mkdtemp()
    try:
        yield Path(tmp)
    finally:
        _fix_docker_permissions(Path(tmp))
        shutil.rmtree(tmp, ignore_errors=True)


def _build_nskit_image() -> bool:
    """Build the nskit runtime Docker image from the repo root.

    Returns:
        True if the build succeeded.
    """
    result = subprocess.run(
        [
            "docker",
            "build",
            "--target",
            "runtime",
            "--build-arg",
            "RECIPE_NAME=python_package",
            "-t",
            DOCKER_IMAGE_TAG,
            ".",
        ],
        cwd=NSKIT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Local engine — real recipe execution
# ---------------------------------------------------------------------------


class TestLocalEngineSmoke(unittest.TestCase):
    """Smoke tests exercising LocalEngine with a real installed recipe."""

    def test_creates_project_files(self) -> None:
        """LocalEngine produces files from the built-in python_package recipe."""
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "my-project"
            engine = LocalEngine()

            result = engine.execute(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "smoke.test.pkg",
                    "repo": {
                        "owner": "Test Owner",
                        "email": "test@example.com",
                        "description": "Smoke test project",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
                entrypoint="nskit.recipes",
            )

            self.assertTrue(result.success, f"LocalEngine failed: {result.errors}")
            self.assertTrue(output_dir.exists())
            self.assertTrue(
                any(p.name == "pyproject.toml" for p in output_dir.rglob("*")),
                "Expected pyproject.toml in generated project",
            )
            self.assertTrue(
                any(p.name == "README.md" for p in output_dir.rglob("*")),
                "Expected README.md in generated project",
            )

    def test_returns_files_created(self) -> None:
        """LocalEngine result includes the files that were created."""
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "files-test"
            engine = LocalEngine()

            result = engine.execute(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "files.check",
                    "repo": {
                        "owner": "Owner",
                        "email": "o@example.com",
                        "description": "desc",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
                entrypoint="nskit.recipes",
            )

            self.assertTrue(result.success)
            self.assertGreater(len(result.files_created), 0)

    def test_missing_entrypoint_raises(self) -> None:
        """LocalEngine raises ValueError when entrypoint is not provided."""
        engine = LocalEngine()
        with self.assertRaises(ValueError):
            engine.execute(
                recipe="python_package",
                version="local",
                parameters={"name": "test"},
                output_dir=Path("/tmp/nope"),
            )

    def test_unknown_recipe_returns_error(self) -> None:
        """LocalEngine returns error result for a non-existent recipe."""
        with TemporaryDirectory() as tmp:
            engine = LocalEngine()
            result = engine.execute(
                recipe="nonexistent_recipe_xyz",
                version="local",
                parameters={},
                output_dir=Path(tmp) / "out",
                entrypoint="nskit.recipes",
            )

            self.assertFalse(result.success)
            self.assertGreater(len(result.errors), 0)


# ---------------------------------------------------------------------------
# Docker engine — real image build + container execution
# ---------------------------------------------------------------------------


@unittest.skipUnless(_docker_available(), "Docker not available")
class TestDockerEngineSmoke(unittest.TestCase):
    """Smoke tests exercising DockerEngine with a real locally-built image.

    These tests build the nskit Docker image once, then run recipes inside
    it to verify the full container-based execution path.
    """

    _image_built: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        """Build the nskit Docker image before running any tests."""
        cls._image_built = _build_nskit_image()
        if not cls._image_built:
            raise unittest.SkipTest("Failed to build nskit Docker image — skipping Docker smoke tests")

    def test_docker_engine_creates_project(self) -> None:
        """DockerEngine generates a project via the containerised CLI."""
        with _docker_tmpdir() as tmp:
            output_dir = tmp / "docker-project"
            output_dir.mkdir()

            engine = DockerEngine(skip_pull=True)
            result = engine.execute(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "docker.smoke.pkg",
                    "repo": {
                        "owner": "Docker Owner",
                        "email": "docker@example.com",
                        "description": "Docker smoke test",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
                image_url=DOCKER_IMAGE_TAG,
            )

            self.assertTrue(result.success, f"DockerEngine failed: {result.errors}")
            self.assertTrue(output_dir.exists())
            self.assertTrue(
                any(p.name == "pyproject.toml" for p in output_dir.rglob("*")),
                "Expected pyproject.toml in Docker-generated project",
            )

    def test_docker_engine_returns_files_created(self) -> None:
        """DockerEngine result lists the files produced by the container."""
        with _docker_tmpdir() as tmp:
            output_dir = tmp / "docker-files"
            output_dir.mkdir()

            engine = DockerEngine(skip_pull=True)
            result = engine.execute(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "docker.files",
                    "repo": {
                        "owner": "O",
                        "email": "o@example.com",
                        "description": "d",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
                image_url=DOCKER_IMAGE_TAG,
            )

            self.assertTrue(result.success)
            self.assertGreater(len(result.files_created), 0)

    def test_docker_engine_bad_image_returns_error(self) -> None:
        """DockerEngine returns error when the image does not exist."""
        with TemporaryDirectory() as tmp:
            engine = DockerEngine(skip_pull=True)
            result = engine.execute(
                recipe="python_package",
                version="v1",
                parameters={},
                output_dir=Path(tmp) / "out",
                image_url="nonexistent-image:never",
            )

            self.assertFalse(result.success)
            self.assertGreater(len(result.errors), 0)


# ---------------------------------------------------------------------------
# RecipeClient orchestration with both engines
# ---------------------------------------------------------------------------


class TestRecipeClientWithLocalEngine(unittest.TestCase):
    """RecipeClient + LocalEngine end-to-end."""

    def _make_backend(self) -> Mock:
        """Create a mock backend."""
        backend = Mock()
        backend.entrypoint = "nskit.recipes"
        backend.get_image_url = Mock(return_value="img:v1")
        backend.pull_image = Mock()
        return backend

    def test_client_creates_project(self) -> None:
        """RecipeClient + LocalEngine produces a real project."""
        backend = self._make_backend()

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "client-local"
            client = RecipeClient(backend, engine=LocalEngine())

            result = client.initialize_recipe(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "client.local.test",
                    "repo": {
                        "owner": "Owner",
                        "email": "o@example.com",
                        "description": "desc",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
            )

            self.assertTrue(result.success, f"Client+Local failed: {result.errors}")
            self.assertTrue(output_dir.exists())
            backend.get_image_url.assert_not_called()
            backend.pull_image.assert_not_called()

    def test_client_rejects_non_empty_dir(self) -> None:
        """RecipeClient refuses to initialise into a non-empty directory."""
        backend = self._make_backend()

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "non-empty"
            output_dir.mkdir()
            (output_dir / "existing.txt").write_text("content")

            client = RecipeClient(backend, engine=LocalEngine())
            result = client.initialize_recipe(
                recipe="python_package",
                version="local",
                parameters={"name": "test"},
                output_dir=output_dir,
            )

            self.assertFalse(result.success)
            self.assertGreater(len(result.errors), 0)


@unittest.skipUnless(_docker_available(), "Docker not available")
class TestRecipeClientWithDockerEngine(unittest.TestCase):
    """RecipeClient + DockerEngine end-to-end with a real image."""

    _image_built: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        """Build the nskit Docker image before running any tests."""
        cls._image_built = _build_nskit_image()
        if not cls._image_built:
            raise unittest.SkipTest("Failed to build nskit Docker image — skipping Docker client tests")

    def _make_backend(self) -> Mock:
        """Create a mock backend that returns the local image tag."""
        backend = Mock()
        backend.entrypoint = "nskit.recipes"
        backend.get_image_url = Mock(return_value=DOCKER_IMAGE_TAG)
        backend.pull_image = Mock()
        return backend

    def test_client_with_docker_creates_project(self) -> None:
        """Full flow: RecipeClient → DockerEngine → container → files on disk."""
        backend = self._make_backend()

        with _docker_tmpdir() as tmp:
            output_dir = tmp / "client-docker"
            client = RecipeClient(backend, engine=DockerEngine(skip_pull=True))

            result = client.initialize_recipe(
                recipe="python_package",
                version="local",
                parameters={
                    "name": "client.docker.test",
                    "repo": {
                        "owner": "Docker Owner",
                        "email": "docker@example.com",
                        "description": "Full flow test",
                        "url": "https://example.com",
                    },
                },
                output_dir=output_dir,
            )

            self.assertTrue(result.success, f"Client+Docker failed: {result.errors}")
            backend.get_image_url.assert_called_once()
            self.assertTrue(
                any(p.name == "pyproject.toml" for p in output_dir.rglob("*")),
                "Expected pyproject.toml from Docker flow",
            )


if __name__ == "__main__":
    unittest.main()
