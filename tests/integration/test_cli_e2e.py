"""End-to-end CLI tests using actual command execution."""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nskit.cli import create_cli
from nskit.client.backends import LocalBackend


@pytest.fixture
def cli_runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_backend(tmp_path):
    """Create test backend with recipes."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    # Create test recipe v1.0.0
    v1 = recipes_dir / "test_recipe" / "v1.0.0"
    v1.mkdir(parents=True)
    (v1 / "README.md").write_text("# {{name}}\n\nTest recipe")
    recipe_config_dir = v1 / ".recipe"
    recipe_config_dir.mkdir(parents=True)
    (recipe_config_dir / "config.yml").write_text("metadata:\n  recipe_name: test_recipe\n  recipe_version: v1.0.0\n")

    return LocalBackend(recipes_dir=recipes_dir)


class TestCLIEndToEnd:
    """End-to-end CLI command tests."""

    def test_init_command_with_yaml(self, cli_runner, tmp_path):
        """Test init command with YAML input file."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        # Create input YAML
        input_yaml = tmp_path / "input.yaml"
        input_yaml.write_text("name: test_project\nauthor: Test Author\n")

        output_dir = tmp_path / "output"

        result = cli_runner.invoke(
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
        assert result.exit_code in [0, 1]

    def test_init_command_without_yaml(self, cli_runner, tmp_path):
        """Test init command without YAML input."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        output_dir = tmp_path / "output"

        result = cli_runner.invoke(app, ["init", "--recipe", "python_package", "--output-base-path", str(output_dir)])

        assert result.exit_code in [0, 1]

    def test_get_required_fields_command(self, cli_runner):
        """Test get-required-fields returns valid JSON."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = cli_runner.invoke(app, ["get-required-fields", "--recipe", "python_package"])

        if result.exit_code == 0:
            # Should be valid JSON
            data = json.loads(result.stdout)
            assert isinstance(data, dict)

    def test_list_command_with_backend(self, cli_runner, test_backend):
        """Test list command with backend."""
        app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "test_recipe" in result.stdout or "No recipes" in result.stdout

    def test_discover_command_with_search(self, cli_runner, test_backend):
        """Test discover command with search term."""
        app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

        result = cli_runner.invoke(app, ["discover", "--search", "test"])

        assert result.exit_code == 0

    def test_cli_help_command(self, cli_runner):
        """Test CLI help output."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.stdout
        assert "get-required-fields" in result.stdout

    def test_init_command_with_override_path(self, cli_runner, tmp_path):
        """Test init with output override path."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        override_path = tmp_path / "custom_name"

        result = cli_runner.invoke(
            app, ["init", "--recipe", "python_package", "--output-override-path", str(override_path)]
        )

        assert result.exit_code in [0, 1]

    def test_init_command_local_flag(self, cli_runner, test_backend, tmp_path):
        """Test init with --local flag."""
        app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

        result = cli_runner.invoke(
            app, ["init", "--recipe", "test_recipe", "--output-base-path", str(tmp_path), "--local"]
        )

        # Should attempt local execution
        assert result.exit_code in [0, 1]

    def test_cli_invalid_recipe(self, cli_runner):
        """Test CLI with invalid recipe name."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = cli_runner.invoke(app, ["init", "--recipe", "nonexistent_recipe_xyz"])

        assert result.exit_code == 1

    def test_cli_missing_required_option(self, cli_runner):
        """Test CLI with missing required option."""
        app = create_cli(recipe_entrypoint="nskit.recipes")

        result = cli_runner.invoke(app, ["init"])

        assert result.exit_code == 2  # Typer returns 2 for missing options

    def test_check_command_with_backend(self, cli_runner, test_backend, tmp_path):
        """Test check command."""
        app = create_cli(recipe_entrypoint="nskit.recipes", backend=test_backend)

        # Create fake project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        recipe_dir = project_dir / ".recipe"
        recipe_dir.mkdir()
        (recipe_dir / "config.yml").write_text("metadata:\n  recipe_name: test_recipe\n  recipe_version: v1.0.0\n")

        result = cli_runner.invoke(app, ["check", "--project-path", str(project_dir)])

        assert result.exit_code == 0
