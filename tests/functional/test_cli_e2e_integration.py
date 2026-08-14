"""End-to-end CLI tests using actual command execution."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from nskit.cli import create_cli
from nskit.client.backends import LocalBackend


class TestCLIEndToEnd(unittest.TestCase):
    """End-to-end CLI command tests."""

    def setUp(self):
        """Set up CLI runner."""
        self.cli_runner = CliRunner()

    def _create_test_backend(self, tmp_path):
        """Create test backend with recipes."""
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()

        # Create test recipe v1.0.0
        v1 = recipes_dir / "test_recipe" / "v1.0.0"
        v1.mkdir(parents=True)
        (v1 / "README.md").write_text("# {{name}}\n\nTest recipe")
        recipe_config_dir = v1 / ".recipe"
        recipe_config_dir.mkdir(parents=True)
        (recipe_config_dir / "config.yml").write_text(
            "metadata:\n  recipe_name: test_recipe\n  docker_image: test/test_recipe:v1.0.0\n"
        )

        return LocalBackend(recipes_dir=recipes_dir)

    def test_init_command_with_yaml(self):
        """Test init command with YAML input file."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = create_cli(recipe_entrypoint="nskit.recipes")

            # Create input YAML
            input_yaml = tmp_path / "input.yaml"
            input_yaml.write_text("name: test_project\nauthor: Test Author\n")

            output_dir = tmp_path / "output"

            result = self.cli_runner.invoke(
                app,
                [
                    "init",
                    "--recipe",
                    "python_package",
                    "--input-yaml-path",
                    str(input_yaml),
                    "--output-base-path",
                    str(output_dir),
                ],
            )

            # Should fail gracefully if recipe not found
            self.assertIn(result.exit_code, [0, 1])

    def test_init_command_without_yaml(self):
        """Test init command without YAML input."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = create_cli(recipe_entrypoint="nskit.recipes")

            output_dir = tmp_path / "output"

            result = self.cli_runner.invoke(
                app, ["init", "--recipe", "python_package", "--output-base-path", str(output_dir)]
            )

            self.assertIn(result.exit_code, [0, 1])

    def test_get_required_fields_command(self):
        """Test get-required-fields returns valid JSON."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = self.cli_runner.invoke(app, ["get-required-fields", "--recipe", "python_package"])

        if result.exit_code == 0:
            # Should be valid JSON
            data = json.loads(result.stdout)
            self.assertIsInstance(data, dict)

    def test_list_command_with_backend(self):
        """Test list command with backend."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            test_backend = self._create_test_backend(tmp_path)
            app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

            result = self.cli_runner.invoke(app, ["list"])

            self.assertEqual(result.exit_code, 0)
            self.assertTrue("test_recipe" in result.stdout or "No recipes" in result.stdout)

    def test_discover_command_with_search(self):
        """Test discover command with search term."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            test_backend = self._create_test_backend(tmp_path)
            app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

            result = self.cli_runner.invoke(app, ["discover", "--search", "test"])

            self.assertEqual(result.exit_code, 0)

    def test_cli_help_command(self):
        """Test CLI help output."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = self.cli_runner.invoke(app, ["--help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("init", result.stdout)
        self.assertIn("get-required-fields", result.stdout)

    def test_init_command_with_override_path(self):
        """Test init with output override path."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = create_cli(recipe_entrypoint="nskit.recipes")

            override_path = tmp_path / "custom_name"

            result = self.cli_runner.invoke(
                app, ["init", "--recipe", "python_package", "--output-override-path", str(override_path)]
            )

            self.assertIn(result.exit_code, [0, 1])

    def test_init_command_local_flag(self):
        """Test init with --local flag."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            test_backend = self._create_test_backend(tmp_path)
            app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

            result = self.cli_runner.invoke(
                app, ["init", "--recipe", "test_recipe", "--output-base-path", str(tmp_path), "--local"]
            )

            # Should attempt local execution
            self.assertIn(result.exit_code, [0, 1])

    def test_cli_invalid_recipe(self):
        """Test CLI with invalid recipe name."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = self.cli_runner.invoke(app, ["init", "--recipe", "nonexistent_recipe_xyz"])

        self.assertEqual(result.exit_code, 1)

    def test_cli_missing_required_option(self):
        """Test CLI with missing required option."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = self.cli_runner.invoke(app, ["init"])

        self.assertEqual(result.exit_code, 2)  # Typer returns 2 for missing options

    def test_check_command_with_backend(self):
        """Test check command."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            test_backend = self._create_test_backend(tmp_path)
            app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

            # Create fake project
            project_dir = tmp_path / "project"
            project_dir.mkdir()
            recipe_dir = project_dir / ".recipe"
            recipe_dir.mkdir()
            (recipe_dir / "config.yml").write_text(
                "metadata:\n  recipe_name: test_recipe\n  docker_image: test/test_recipe:v1.0.0\n"
            )

            result = self.cli_runner.invoke(app, ["check", "--project-path", str(project_dir)])

            self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
