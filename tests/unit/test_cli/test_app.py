"""Tests for CLI factory."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from nskit.cli import create_cli


@pytest.fixture
def mock_backend():
    """Mock backend for testing."""
    backend = Mock()
    backend.list_recipes.return_value = []
    backend.get_recipe_versions.return_value = ["v1.0.0"]
    return backend


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


class TestCreateCLI:
    """Test CLI factory."""

    def test_create_cli_basic(self):
        """Test creating basic CLI without backend."""
        app = create_cli(recipe_entrypoint="test.recipes", app_name="test-cli", app_help="Test CLI")

        assert app is not None
        assert app.info.name == "test-cli"
        assert app.info.help == "Test CLI"

    def test_create_cli_with_backend(self, mock_backend):
        """Test creating CLI with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=mock_backend)

        assert app is not None

    def test_init_command_exists(self, runner):
        """Test init command is registered."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "init" in result.stdout

    def test_get_required_fields_command_exists(self, runner):
        """Test get-required-fields command is registered."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "get-required-fields" in result.stdout

    def test_list_command_with_backend(self, runner, mock_backend):
        """Test list command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=mock_backend)
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout

    def test_list_command_without_backend(self, runner):
        """Test list command is available without backend (uses entry points)."""
        app = create_cli(recipe_entrypoint="test.recipes")
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "list" in result.stdout

    def test_update_command_with_backend(self, runner, mock_backend):
        """Test update command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=mock_backend)
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "update" in result.stdout

    def test_check_command_with_backend(self, runner, mock_backend):
        """Test check command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=mock_backend)
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "check" in result.stdout

    def test_discover_command_with_backend(self, runner, mock_backend):
        """Test discover command is available with backend."""
        app = create_cli(recipe_entrypoint="test.recipes", backend=mock_backend)
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "discover" in result.stdout

    @patch("nskit.mixer.components.recipe.Recipe.load")
    def test_init_command_without_backend(self, mock_load, runner, tmp_path):
        """Test init command works without backend."""
        mock_recipe = Mock()
        mock_load.return_value = mock_recipe

        app = create_cli(recipe_entrypoint="test.recipes")

        # Use input-yaml-path to skip interactive prompting
        input_file = tmp_path / "input.yaml"
        input_file.write_text("name: test\n")

        runner.invoke(
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
    def test_get_required_fields_command(self, mock_load, runner):
        """Test get-required-fields command."""
        mock_recipe = Mock()
        mock_load.return_value = mock_recipe

        app = create_cli(recipe_entrypoint="test.recipes")

        with patch("nskit.cli.app.get_required_fields_as_dict", return_value={"field1": "str"}):
            result = runner.invoke(app, ["get-required-fields", "--recipe", "test_recipe"])

            assert result.exit_code == 0
            assert "field1" in result.stdout
