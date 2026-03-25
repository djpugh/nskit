"""End-to-end tests for the CLI workflows using CliRunner.

Tests the full CLI surface: list, get-required-fields, init (YAML mode),
and the interactive default resolution chain (via mocked questionary).
"""
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from typer.testing import CliRunner

from nskit.cli.app import create_cli


class TestCLIListCommand(unittest.TestCase):
    """Test nskit list discovers installed recipes."""

    def test_list_shows_installed_recipes(self):
        app = create_cli(recipe_entrypoint="nskit.recipes")
        result = CliRunner().invoke(app, ["list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("python_package", result.stdout)
        self.assertIn("recipe", result.stdout)
        self.assertIn("python_api_service", result.stdout)

    def test_list_with_backend_queries_backend(self):
        from nskit.client.models import RecipeInfo

        backend = Mock()
        backend.list_recipes.return_value = [
            RecipeInfo(name="backend-recipe", versions=["v1.0.0", "v2.0.0"]),
        ]
        app = create_cli(recipe_entrypoint="nskit.recipes", backend=backend)
        result = CliRunner().invoke(app, ["list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("backend-recipe", result.stdout)
        self.assertIn("v1.0.0", result.stdout)


class TestCLIGetRequiredFields(unittest.TestCase):
    """Test nskit get-required-fields returns field specs."""

    def test_returns_json(self):
        app = create_cli(recipe_entrypoint="nskit.recipes")
        result = CliRunner().invoke(app, ["get-required-fields", "--recipe", "python_package"])
        self.assertEqual(result.exit_code, 0)
        fields = json.loads(result.stdout)
        self.assertIn("name", fields)
        self.assertIn("repo.owner", fields)
        self.assertIn("repo.email", fields)
        self.assertIn("repo.url", fields)


class TestCLIInitYAML(unittest.TestCase):
    """Test nskit init with --input-yaml-path (no interactive prompting)."""

    def test_creates_project_from_yaml(self):
        with TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "input.yaml"
            input_file.write_text(
                "name: cli-yaml-test\n"
                "repo:\n"
                "  owner: CLI Tester\n"
                "  email: cli@test.com\n"
                "  description: CLI e2e test\n"
                "  url: https://example.com\n"
            )
            app = create_cli(recipe_entrypoint="nskit.recipes")
            result = CliRunner().invoke(
                app,
                [
                    "init",
                    "--recipe",
                    "python_package",
                    "--input-yaml-path",
                    str(input_file),
                    "--output-base-path",
                    tmp,
                ],
            )
            self.assertEqual(result.exit_code, 0, f"Failed: {result.exception}")
            project = Path(tmp) / "cli-yaml-test"
            self.assertTrue((project / "pyproject.toml").exists())
            self.assertTrue((project / "README.md").exists())
            self.assertTrue((project / "src").is_dir())
            self.assertTrue((project / ".git").is_dir())

    def test_fails_on_missing_fields(self):
        with TemporaryDirectory() as tmp:
            input_file = Path(tmp) / "input.yaml"
            input_file.write_text("name: incomplete\n")
            app = create_cli(recipe_entrypoint="nskit.recipes")
            result = CliRunner().invoke(
                app,
                [
                    "init",
                    "--recipe",
                    "python_package",
                    "--input-yaml-path",
                    str(input_file),
                    "--output-base-path",
                    tmp,
                ],
            )
            # Should fail because repo is missing
            self.assertNotEqual(result.exit_code, 0)


class TestCLIInitInteractive(unittest.TestCase):
    """Test the interactive init default resolution chain.

    Questionary needs a real terminal, so we mock it and verify
    the defaults passed to each prompt.
    """

    def _run_init_interactive(self, env=None, ctx=None, model_fields=None, fields=None):
        """Run init in interactive mode, return {field_name: default_passed}."""
        collected = {}

        def fake_text(prompt, default=""):
            collected[prompt] = default
            return MagicMock(ask=Mock(return_value=default or "val"))

        def fake_confirm(prompt, default=False):
            collected[prompt] = default
            return MagicMock(ask=Mock(return_value=default))

        mock_recipe = Mock()
        mock_recipe.model_fields = model_fields or {}

        with (
            patch("nskit.cli.app.questionary") as mock_q,
            patch("nskit.cli.app.Recipe.load", return_value=mock_recipe),
            patch("nskit.cli.app.get_required_fields_as_dict", return_value=fields or {"name": "str"}),
            patch("nskit.cli.app.ContextProvider") as mock_ctx_cls,
            patch("nskit.cli.app.EnvVarResolver") as mock_resolver_cls,
        ):
            mock_q.text = fake_text
            mock_q.confirm = fake_confirm
            mock_q.select = lambda p, choices=None, default=None: MagicMock(
                ask=Mock(return_value=default or choices[0])
            )

            resolver = Mock()
            resolver.resolve.side_effect = lambda name: (env or {}).get(name)
            mock_resolver_cls.return_value = resolver
            mock_ctx_cls.return_value.get_context.return_value = ctx or {}

            app = create_cli(recipe_entrypoint="nskit.recipes")
            with TemporaryDirectory() as tmp:
                CliRunner().invoke(app, ["init", "--recipe", "python_package", "--output-base-path", tmp])

        return collected

    def test_convention_env_var_populates_default(self):
        """RECIPE_NAME → name field default."""
        defaults = self._run_init_interactive(
            env={"RECIPE_NAME": "from-env"},
            fields={"name": "str"},
        )
        self.assertEqual(defaults["name"], "from-env")

    def test_nested_convention_env_var(self):
        """RECIPE_REPO_OWNER → repo.owner field default."""
        defaults = self._run_init_interactive(
            env={"RECIPE_REPO_OWNER": "EnvOwner"},
            fields={"repo.owner": "str"},
        )
        self.assertEqual(defaults["repo.owner"], "EnvOwner")

    def test_git_email_context_fallback(self):
        """git_email context → repo.email default."""
        defaults = self._run_init_interactive(
            ctx={"git_email": "git@ctx.com"},
            fields={"repo.email": "str"},
        )
        self.assertEqual(defaults["repo.email"], "git@ctx.com")

    def test_git_name_context_fallback(self):
        """git_name context → repo.owner default."""
        defaults = self._run_init_interactive(
            ctx={"git_name": "Git User"},
            fields={"repo.owner": "str"},
        )
        self.assertEqual(defaults["repo.owner"], "Git User")

    def test_env_var_beats_context(self):
        """Env var takes priority over context."""
        defaults = self._run_init_interactive(
            env={"RECIPE_REPO_OWNER": "EnvWins"},
            ctx={"git_name": "ContextLoses"},
            fields={"repo.owner": "str"},
        )
        self.assertEqual(defaults["repo.owner"], "EnvWins")

    def test_recipe_field_env_var_priority(self):
        """RecipeField(env_var=...) beats convention env var."""
        field_info = Mock()
        field_info.json_schema_extra = {"env_var": "CUSTOM_VAR"}
        defaults = self._run_init_interactive(
            env={"CUSTOM_VAR": "custom", "RECIPE_NAME": "convention"},
            fields={"name": "str"},
            model_fields={"name": field_info},
        )
        self.assertEqual(defaults["name"], "custom")

    def test_template_evaluated_with_collected_values(self):
        """RecipeField(template=...) evaluated against already-collected values."""
        slug_info = Mock()
        slug_info.json_schema_extra = {"template": "{{name | lower}}"}
        name_info = Mock()
        name_info.json_schema_extra = {}

        collected = {}
        call_idx = [0]

        def fake_text(prompt, default=""):
            collected[prompt] = default
            m = MagicMock()
            if call_idx[0] == 0:
                m.ask.return_value = "MyProject"
            else:
                m.ask.return_value = default or "val"
            call_idx[0] += 1
            return m

        mock_recipe = Mock()
        mock_recipe.model_fields = {"name": name_info, "slug": slug_info}

        with (
            patch("nskit.cli.app.questionary") as mock_q,
            patch("nskit.cli.app.Recipe.load", return_value=mock_recipe),
            patch("nskit.cli.app.get_required_fields_as_dict", return_value={"name": "str", "slug": "str"}),
            patch("nskit.cli.app.ContextProvider") as mock_ctx_cls,
            patch("nskit.cli.app.EnvVarResolver") as mock_resolver_cls,
        ):
            mock_q.text = fake_text
            mock_q.confirm = lambda p, default=False: MagicMock(ask=Mock(return_value=default))
            mock_resolver_cls.return_value = Mock(resolve=Mock(return_value=None))
            mock_ctx_cls.return_value.get_context.return_value = {}

            app = create_cli(recipe_entrypoint="nskit.recipes")
            with TemporaryDirectory() as tmp:
                CliRunner().invoke(app, ["init", "--recipe", "python_package", "--output-base-path", tmp])

        self.assertEqual(collected["slug"], "myproject")

    def test_no_defaults_gives_empty_string(self):
        """No env vars, no context → empty default."""
        defaults = self._run_init_interactive(
            fields={"custom_field": "str"},
            ctx={},
        )
        self.assertEqual(defaults["custom_field"], "")

    def test_bool_field_uses_confirm(self):
        """Bool fields prompt with confirm."""
        collected = {}

        def fake_confirm(prompt, default=False):
            collected["_confirm_called"] = True
            return MagicMock(ask=Mock(return_value=default))

        mock_recipe = Mock()
        mock_recipe.model_fields = {}

        with (
            patch("nskit.cli.app.questionary") as mock_q,
            patch("nskit.cli.app.Recipe.load", return_value=mock_recipe),
            patch("nskit.cli.app.get_required_fields_as_dict", return_value={"flag": "bool"}),
            patch("nskit.cli.app.ContextProvider") as mock_ctx_cls,
            patch("nskit.cli.app.EnvVarResolver") as mock_resolver_cls,
        ):
            mock_q.text = lambda p, default="": MagicMock(ask=Mock(return_value="x"))
            mock_q.confirm = fake_confirm
            mock_resolver_cls.return_value = Mock(resolve=Mock(return_value=None))
            mock_ctx_cls.return_value.get_context.return_value = {}

            app = create_cli(recipe_entrypoint="nskit.recipes")
            with TemporaryDirectory() as tmp:
                CliRunner().invoke(app, ["init", "--recipe", "python_package", "--output-base-path", tmp])

        self.assertTrue(collected.get("_confirm_called"))


if __name__ == "__main__":
    unittest.main()
