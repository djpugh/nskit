"""Tests for Docker execution mode."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.recipes import RecipeClient


class TestDockerExecution(unittest.TestCase):
    """Test Docker execution pathway."""

    def setUp(self):
        """Create mock backend and temporary directory."""
        self.mock_backend = Mock()
        self.mock_backend.entrypoint = "test.recipes"
        self.mock_backend.get_image_url = Mock(return_value="ghcr.io/test/recipe:v1.0.0")
        self.mock_backend.pull_image = Mock()

        self._tmp_dir = TemporaryDirectory()
        self.tmp_path = Path(self._tmp_dir.name)

    def tearDown(self):
        """Clean up temporary directory."""
        self._tmp_dir.cleanup()

    def test_docker_mode_pulls_image(self):
        """Test that Docker mode pulls image."""
        client = RecipeClient(self.mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=self.tmp_path / "output",
            )

        # Verify image was pulled
        self.mock_backend.get_image_url.assert_called_once_with("test-recipe", "v1.0.0")
        self.mock_backend.pull_image.assert_called_once_with("ghcr.io/test/recipe:v1.0.0")

    def test_docker_mode_runs_container(self):
        """Test that Docker mode runs container with correct arguments."""
        client = RecipeClient(self.mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test", "version": "1.0"},
                output_dir=self.tmp_path / "output",
            )

        # Verify docker run was called (find the init call, not the chown)
        self.assertTrue(mock_run.called)
        run_calls = [
            c[0][0] for c in mock_run.call_args_list if c[0][0][0:2] == ["docker", "run"] and "init" in c[0][0]
        ]
        self.assertEqual(len(run_calls), 1)
        call_args = run_calls[0]
        self.assertIn("--rm", call_args)
        self.assertIn("ghcr.io/test/recipe:v1.0.0", call_args)

    def test_docker_mode_mounts_volumes(self):
        """Test that Docker mode mounts output directory."""
        client = RecipeClient(self.mock_backend, engine=DockerEngine())
        output_dir = self.tmp_path / "output"

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
        self.assertEqual(len(run_calls), 1)
        call_args = run_calls[0]
        self.assertIn("-v", call_args)
        # Find the output volume mount
        v_index = [i for i, arg in enumerate(call_args) if arg == "-v"]
        self.assertTrue(any(f"{output_dir.absolute()}:/app/output" in call_args[i + 1] for i in v_index))

    def test_docker_mode_passes_parameters(self):
        """Docker mode writes parameters to a YAML file and mounts it as input.

        Asserts on the mount and contents rather than the tempfile API, so the
        staging location is an implementation detail.
        """
        import yaml

        client = RecipeClient(self.mock_backend, engine=DockerEngine())
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
                    output_dir = self.tmp_path / "output"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    (output_dir / "generated.txt").write_text("x")
            return Mock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=capture):
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters=params,
                output_dir=self.tmp_path / "output",
            )

        self.assertTrue(result.success, result.errors)
        self.assertEqual(staged["contents"], params)
        # Staging dir cleaned up after the run.
        self.assertFalse(staged["path"].exists())

    def test_input_not_staged_inside_output_directory(self):
        """The input file must not land inside the generated project.

        Recipe post-hooks (git init) run against the output directory, and
        parameters may contain secrets.
        """
        client = RecipeClient(self.mock_backend, engine=DockerEngine())
        output_dir = self.tmp_path / "output"
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

        self.assertTrue(result.success, result.errors)
        self.assertNotIn(output_dir, seen[0].parents)

    def test_no_files_produced_is_reported_as_error(self):
        """A clean exit producing nothing must fail, not silently succeed.

        Docker creates an empty directory at the mount target when the host path
        is unshared, so the recipe runs inside the container but the host sees
        nothing.
        """
        client = RecipeClient(self.mock_backend, engine=DockerEngine())

        with patch("subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")):
            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=self.tmp_path / "output",
            )

        self.assertFalse(result.success)
        self.assertTrue(any("produced no files" in e for e in result.errors))

    def test_local_mode_uses_installed_package(self):
        """Test that local mode uses installed package."""
        client = RecipeClient(self.mock_backend, engine=LocalEngine())

        with patch("nskit.mixer.components.Recipe.load") as mock_load:
            mock_recipe = Mock()
            mock_recipe.create = Mock(return_value={"file1.txt": "content"})
            mock_load.return_value = mock_recipe

            client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={"name": "test"},
                output_dir=self.tmp_path / "output",
            )

        # Verify Recipe.load was called
        mock_load.assert_called_once()
        mock_recipe.create.assert_called_once()

        # Verify backend methods were NOT called
        self.mock_backend.get_image_url.assert_not_called()
        self.mock_backend.pull_image.assert_not_called()

    def test_execution_mode_can_be_changed(self):
        """Test that engine can be changed after initialization."""
        client = RecipeClient(self.mock_backend, engine=DockerEngine())
        self.assertIsInstance(client.engine, DockerEngine)

        client.engine = LocalEngine()
        self.assertIsInstance(client.engine, LocalEngine)

    def test_docker_mode_handles_container_failure(self):
        """Test that Docker mode handles container execution failures."""
        client = RecipeClient(self.mock_backend, engine=DockerEngine())

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Container failed")

            result = client.initialize_recipe(
                recipe="test-recipe",
                version="v1.0.0",
                parameters={},
                output_dir=self.tmp_path / "output",
            )

        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("Container failed", result.errors[0])


class TestEngines(unittest.TestCase):
    """Test execution engines."""

    def test_docker_engine_exists(self):
        """Test DockerEngine class exists."""
        self.assertIsNotNone(DockerEngine)

    def test_local_engine_exists(self):
        """Test LocalEngine class exists."""
        self.assertIsNotNone(LocalEngine)


if __name__ == "__main__":
    unittest.main()
