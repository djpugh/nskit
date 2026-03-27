"""Tests for CLI interactive init logic — default resolution chain and field prompting."""

import os
import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from pydantic import Field
from typer.testing import CliRunner

from nskit.cli import create_cli
from nskit.common.contextmanagers import Env
from nskit.mixer.components.recipe import Recipe


def _make_app():
    return create_cli(recipe_entrypoint="nskit.recipes")


class _StubRecipe(Recipe):
    """Minimal recipe for testing field introspection."""

    name: str = "default"


class TestInteractiveInitDefaults(unittest.TestCase):
    """Test the default resolution chain in interactive init."""

    def _run_interactive(self, fields_dict, model_fields_dict=None, env=None, ctx=None, q_text_side_effect=None):
        """Helper: run init in interactive mode, capturing questionary calls.

        Returns dict of {prompt_label: default_passed_to_questionary}.
        """
        collected_defaults = {}
        call_order = []

        def fake_text(prompt, default=""):
            collected_defaults[prompt] = default
            call_order.append(("text", prompt))
            m = MagicMock()
            m.ask.return_value = q_text_side_effect(prompt, default) if q_text_side_effect else (default or "val")
            return m

        def fake_confirm(prompt, default=False):
            collected_defaults[prompt] = default
            call_order.append(("confirm", prompt))
            m = MagicMock()
            m.ask.return_value = default
            return m

        def fake_select(prompt, choices=None, default=None):
            collected_defaults[prompt] = {"choices": choices, "default": default}
            call_order.append(("select", prompt))
            m = MagicMock()
            m.ask.return_value = default or choices[0]
            return m

        mock_recipe = Mock()
        mock_recipe.model_fields = model_fields_dict or {}

        with ExitStack() as stack:
            mock_q = stack.enter_context(patch("nskit.cli.app.questionary"))
            stack.enter_context(patch("nskit.cli.app.Recipe.load", return_value=mock_recipe))
            stack.enter_context(patch("nskit.cli.app.get_required_fields_as_dict", return_value=fields_dict))
            mock_ctx_cls = stack.enter_context(patch("nskit.cli.app.ContextProvider"))
            mock_resolver_cls = stack.enter_context(patch("nskit.cli.app.EnvVarResolver"))

            mock_q.text = fake_text
            mock_q.confirm = fake_confirm
            mock_q.select = fake_select

            resolver = Mock()
            resolver.resolve.side_effect = lambda name: (env or {}).get(name)
            mock_resolver_cls.return_value = resolver

            mock_ctx_cls.return_value.get_context.return_value = ctx or {}

            app = _make_app()
            runner = CliRunner()
            with TemporaryDirectory() as tmp:
                runner.invoke(app, ["init", "--recipe", "python_package", "--output-base-path", tmp])

        return collected_defaults, call_order

    def test_env_var_convention_default(self):
        """RECIPE_NAME env var pre-fills the name field."""
        defaults, _ = self._run_interactive(
            fields_dict={"name": "str"},
            env={"RECIPE_NAME": "env-project"},
        )
        self.assertEqual(defaults["name"], "env-project")

    def test_nested_env_var_default(self):
        """RECIPE_REPO_OWNER env var pre-fills repo.owner."""
        defaults, _ = self._run_interactive(
            fields_dict={"repo.owner": "str"},
            env={"RECIPE_REPO_OWNER": "EnvOwner"},
        )
        self.assertEqual(defaults["repo.owner"], "EnvOwner")

    def test_context_fallback_git_email(self):
        """Context provider git_email fills repo.email when no env var set."""
        defaults, _ = self._run_interactive(
            fields_dict={"repo.email": "str"},
            ctx={"git_email": "git@test.com"},
        )
        self.assertEqual(defaults["repo.email"], "git@test.com")

    def test_context_fallback_git_name_for_owner(self):
        """Context provider git_name fills repo.owner when no env var set."""
        defaults, _ = self._run_interactive(
            fields_dict={"repo.owner": "str"},
            ctx={"git_name": "Git User"},
        )
        self.assertEqual(defaults["repo.owner"], "Git User")

    def test_env_var_beats_context(self):
        """Env var takes priority over context fallback."""
        defaults, _ = self._run_interactive(
            fields_dict={"repo.owner": "str"},
            env={"RECIPE_REPO_OWNER": "EnvOwner"},
            ctx={"git_name": "ContextOwner"},
        )
        self.assertEqual(defaults["repo.owner"], "EnvOwner")

    def test_recipe_field_env_var_takes_priority(self):
        """RecipeField(env_var=...) takes priority over convention env var."""
        field_info = Mock()
        field_info.json_schema_extra = {"env_var": "CUSTOM_NAME"}

        defaults, _ = self._run_interactive(
            fields_dict={"name": "str"},
            model_fields_dict={"name": field_info},
            env={"CUSTOM_NAME": "custom-val", "RECIPE_NAME": "convention-val"},
        )
        self.assertEqual(defaults["name"], "custom-val")

    def test_template_default_evaluated(self):
        """RecipeField(template=...) is evaluated with collected values."""
        slug_info = Mock()
        slug_info.json_schema_extra = {"template": "{{name | lower}}"}
        name_info = Mock()
        name_info.json_schema_extra = {}

        call_idx = [0]

        def side_effect(prompt, default):
            call_idx[0] += 1
            if call_idx[0] == 1:
                return "MyProject"  # name
            return default or "val"  # slug should get template default

        defaults, _ = self._run_interactive(
            fields_dict={"name": "str", "slug": "str"},
            model_fields_dict={"name": name_info, "slug": slug_info},
            q_text_side_effect=side_effect,
        )
        self.assertEqual(defaults["slug"], "myproject")

    def test_options_field_uses_select(self):
        """RecipeField(options=[...]) triggers questionary.select."""
        field_info = Mock()
        field_info.json_schema_extra = {"options": ["aws", "gcp", "azure"]}

        defaults, calls = self._run_interactive(
            fields_dict={"cloud": "str"},
            model_fields_dict={"cloud": field_info},
        )
        self.assertTrue(any(c[0] == "select" for c in calls))
        self.assertEqual(defaults["cloud"]["choices"], ["aws", "gcp", "azure"])

    def test_bool_field_uses_confirm(self):
        """Bool fields use questionary.confirm."""
        _, calls = self._run_interactive(fields_dict={"use_docker": "bool"})
        self.assertTrue(any(c[0] == "confirm" for c in calls))

    def test_no_env_no_context_empty_default(self):
        """Without env vars or context, default is empty string."""
        defaults, _ = self._run_interactive(
            fields_dict={"custom_field": "str"},
            ctx={},
        )
        self.assertEqual(defaults["custom_field"], "")

    @patch("nskit.mixer.components.recipe.Recipe.load")
    def test_yaml_input_skips_interactive(self, mock_load):
        """Providing --input-yaml-path skips interactive prompting entirely."""
        mock_recipe = Mock()
        mock_load.return_value = mock_recipe

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_file = tmp_path / "input.yaml"
            input_file.write_text("name: yaml-project\nrepo:\n  owner: YamlOwner\n")

            app = _make_app()
            runner = CliRunner()
            # Remove VCS tokens so _detect_repo_client doesn't trigger questionary
            with Env(remove=["GITHUB_TOKEN", "AZURE_DEVOPS_TOKEN"]):
                runner.invoke(
                    app,
                    [
                        "init",
                        "--recipe",
                        "python_package",
                        "--input-yaml-path",
                        str(input_file),
                        "--output-base-path",
                        str(tmp_path),
                    ],
                )

            mock_load.assert_called_once()
            call_kwargs = mock_load.call_args[1]
            self.assertEqual(call_kwargs["name"], "yaml-project")


if __name__ == "__main__":
    unittest.main()
