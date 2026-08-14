"""Tests for CLI factory."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from typer.testing import CliRunner

from nskit.cli import create_cli
from nskit.common.contextmanagers import Env


class TestCreateCLI(unittest.TestCase):
    """Test CLI factory."""

    def setUp(self):
        self.runner = CliRunner()
        self.mock_backend = Mock()
        self.mock_backend.list_recipes.return_value = []
        self.mock_backend.get_recipe_versions.return_value = ["v1.0.0"]

    def test_create_cli_basic(self):
        """Test creating basic CLI without backend."""
        app = create_cli(recipe_entrypoint="test.recipes", app_name="test-cli", app_help="Test CLI")

        self.assertIsNotNone(app)
        self.assertEqual(app.info.name, "test-cli")
        self.assertEqual(app.info.help, "Test CLI")

    def test_create_cli_with_backend(self):
        """Test creating CLI with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=self.mock_backend)

        self.assertIsNotNone(app)

    def test_init_command_exists(self):
        """Test init command is registered."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("init", result.stdout)

    def test_get_required_fields_command_exists(self):
        """Test get-required-fields command is registered."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("get-required-fields", result.stdout)

    def test_list_command_with_backend(self):
        """Test list command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=self.mock_backend)
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("list", result.stdout)

    def test_list_command_without_backend(self):
        """Test list command is available without backend (uses entry points)."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("list", result.stdout)

    def test_update_command_with_backend(self):
        """Test update command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=self.mock_backend)
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("update", result.stdout)

    def test_check_command_with_backend(self):
        """Test check command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=self.mock_backend)
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("check", result.stdout)

    def test_discover_command_with_backend(self):
        """Test discover command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=self.mock_backend)
        result = self.runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("discover", result.stdout)

    @patch("nskit.mixer.components.recipe.Recipe.load")
    def test_init_command_without_backend(self, mock_load):
        """Test init command works without backend."""
        mock_recipe = Mock()
        mock_load.return_value = mock_recipe

        app = create_cli(recipe_entrypoint="test.recipes")

        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_path = Path(tmp_path)
            # Use input-yaml-path to skip interactive prompting
            input_file = tmp_path / "input.yaml"
            input_file.write_text("name: test\n")

            # Remove VCS tokens so _detect_repo_client doesn't trigger questionary
            with Env(remove=["GITHUB_TOKEN", "AZURE_DEVOPS_TOKEN"]):
                self.runner.invoke(
                    app,
                    [
                        "init",
                        "--recipe",
                        "test_recipe",
                        "--input-yaml-path",
                        str(input_file),
                        "--output-base-path",
                        str(tmp_path),
                    ],
                )

        mock_load.assert_called_once()
        mock_recipe.create.assert_called_once()

    @patch("nskit.mixer.components.recipe.Recipe.load")
    def test_get_required_fields_command(self, mock_load):
        """Test get-required-fields command."""
        mock_recipe = Mock()
        mock_load.return_value = mock_recipe

        app = create_cli(recipe_entrypoint="test.recipes")

        with patch("nskit.cli.app.get_required_fields_as_dict", return_value={"field1": "str"}):
            result = self.runner.invoke(app, ["get-required-fields", "--recipe", "test_recipe"])

            self.assertEqual(result.exit_code, 0)
            self.assertIn("field1", result.stdout)


class TestCommitAndMaybePush(unittest.TestCase):
    """Tests for _commit_and_maybe_push."""

    def test_commits_files(self):
        """Always commits generated files."""
        import subprocess

        from rich.console import Console

        from nskit.cli.app import _commit_and_maybe_push

        with tempfile.TemporaryDirectory() as tmp_path:
            project = Path(tmp_path) / "proj"
            project.mkdir()
            subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=project, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=project, capture_output=True)
            (project / "file.txt").write_text("content")

            console = Console()
            _commit_and_maybe_push(project, "proj", "", False, None, console)

            # Verify commit happened
            result = subprocess.run(["git", "log", "--oneline"], cwd=project, capture_output=True, text=True)
            self.assertIn("Initial commit from recipe", result.stdout)

    def test_skips_without_git(self):
        """Does nothing if project has no .git directory."""
        from rich.console import Console

        from nskit.cli.app import _commit_and_maybe_push

        with tempfile.TemporaryDirectory() as tmp_path:
            project = Path(tmp_path) / "proj"
            project.mkdir()
            (project / "file.txt").write_text("content")

            console = Console()
            # Should not raise
            _commit_and_maybe_push(project, "proj", "", False, None, console)

    def test_creates_remote_and_pushes(self):
        """Creates remote and pushes when create_repo is True."""
        import subprocess

        from rich.console import Console

        from nskit.cli.app import _commit_and_maybe_push

        with tempfile.TemporaryDirectory() as tmp_path:
            project = Path(tmp_path) / "proj"
            project.mkdir()
            subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=project, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=project, capture_output=True)
            (project / "file.txt").write_text("content")

            mock_vcs = MagicMock()
            mock_vcs.get_remote_url.return_value = "https://github.com/org/proj"
            mock_vcs.get_clone_url.return_value = "https://github.com/org/proj.git"

            console = Console()
            with patch("nskit.recipes.repository_client.subprocess.run", return_value=MagicMock(returncode=0)):
                _commit_and_maybe_push(project, "proj", "desc", True, mock_vcs, console)

            mock_vcs.create.assert_called_once_with("proj")

    def test_no_push_when_declined(self):
        """Does not create remote when create_repo is False."""
        import subprocess

        from rich.console import Console

        from nskit.cli.app import _commit_and_maybe_push

        with tempfile.TemporaryDirectory() as tmp_path:
            project = Path(tmp_path) / "proj"
            project.mkdir()
            subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=project, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=project, capture_output=True)
            (project / "file.txt").write_text("content")

            mock_vcs = MagicMock()
            console = Console()
            _commit_and_maybe_push(project, "proj", "", False, mock_vcs, console)

            mock_vcs.create.assert_not_called()


class TestListJsonFlag(unittest.TestCase):
    """``list --json`` outputs a machine-readable JSON array."""

    def setUp(self):
        self.runner = CliRunner()
        self.app = create_cli(recipe_entrypoint="nskit.recipes")

    def test_list_json_exits_zero(self):
        result = self.runner.invoke(self.app, ["list", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)

    def test_list_json_outputs_valid_json(self):
        result = self.runner.invoke(self.app, ["list", "--json"])
        data = json.loads(result.output)
        self.assertIsInstance(data, list)

    def test_list_json_contains_registered_recipes(self):
        result = self.runner.invoke(self.app, ["list", "--json"])
        data = json.loads(result.output)
        self.assertIn("python_package", data)

    def test_list_json_is_sorted(self):
        result = self.runner.invoke(self.app, ["list", "--json"])
        data = json.loads(result.output)
        self.assertEqual(data, sorted(data))

    def test_list_without_json_shows_table(self):
        """Without --json, output is a rich table (not JSON)."""
        result = self.runner.invoke(self.app, ["list"])
        self.assertEqual(result.exit_code, 0)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(result.output)


if __name__ == "__main__":
    unittest.main()
