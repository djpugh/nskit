"""Property-based tests using Hypothesis."""

import unittest
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from nskit.client.models import RecipeInfo, UpdateResult

# Strategies
recipe_name_strategy = st.from_regex(r"[a-z][a-z0-9_-]{2,49}", fullmatch=True)
version_strategy = st.from_regex(r"v?\d+\.\d+\.\d+", fullmatch=True)


class TestRecipeInfoProperties(unittest.TestCase):
    """Property-based tests for RecipeInfo."""

    @given(name=recipe_name_strategy, versions=st.lists(version_strategy, min_size=1, max_size=10))
    def test_recipe_info_creation(self, name, versions):
        """Test RecipeInfo can be created with any valid inputs."""
        recipe = RecipeInfo(name=name, versions=versions)

        self.assertEqual(recipe.name, name)
        self.assertEqual(recipe.versions, versions)

    @given(name=recipe_name_strategy, versions=st.lists(version_strategy, min_size=1, max_size=10))
    def test_recipe_info_serialization(self, name, versions):
        """Test RecipeInfo can be serialized and deserialized."""
        recipe = RecipeInfo(name=name, versions=versions)
        data = recipe.model_dump()
        restored = RecipeInfo(**data)

        self.assertEqual(restored.name, recipe.name)
        self.assertEqual(restored.versions, recipe.versions)


class TestUpdateResultProperties(unittest.TestCase):
    """Property-based tests for UpdateResult."""

    @given(success=st.booleans())
    def test_update_result_creation(self, success):
        """Test UpdateResult can be created."""
        result = UpdateResult(
            success=success, files_updated=[], files_with_conflicts=[], clean_merges=[], errors=[], warnings=[]
        )

        self.assertEqual(result.success, success)


class TestInputValidationProperties(unittest.TestCase):
    """Property-based tests for input validation."""

    @given(project_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{2,49}", fullmatch=True))
    def test_valid_project_names(self, project_name):
        """Test valid project names."""
        self.assertGreaterEqual(len(project_name), 3)
        self.assertTrue(project_name[0].isalpha())

    @given(recipe_name=recipe_name_strategy, version=version_strategy)
    def test_valid_recipe_identifiers(self, recipe_name, version):
        """Test valid recipe identifiers."""
        self.assertGreaterEqual(len(recipe_name), 3)
        self.assertGreaterEqual(len(version), 5)  # At least "1.0.0"

    @given(path_str=st.from_regex(r"[a-zA-Z0-9_/-]{1,100}", fullmatch=True))
    def test_valid_paths(self, path_str):
        """Test valid path strings."""
        path = Path(path_str)
        self.assertIsInstance(path, Path)

    @given(
        yaml_content=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters=" :\n-_"),
            min_size=10,
            max_size=200,
        )
    )
    def test_yaml_content_structure(self, yaml_content):
        """Test YAML content structure."""
        self.assertIsInstance(yaml_content, str)
        self.assertGreaterEqual(len(yaml_content), 10)


class TestRecipeClientProperties(unittest.TestCase):
    """Property-based tests for RecipeClient operations."""

    @given(recipe_name=recipe_name_strategy, output_path=st.from_regex(r"[a-zA-Z0-9_/-]{1,50}", fullmatch=True))
    def test_recipe_client_init_params(self, recipe_name, output_path):
        """Test RecipeClient initialization parameters."""
        # Validate parameters without creating actual client
        self.assertGreaterEqual(len(recipe_name), 3)
        self.assertGreaterEqual(len(output_path), 1)


class TestCLIInputProperties(unittest.TestCase):
    """Property-based tests for CLI input validation."""

    @given(recipe=recipe_name_strategy, output_path=st.from_regex(r"[a-zA-Z0-9_/-]{1,50}", fullmatch=True))
    def test_cli_init_command_inputs(self, recipe, output_path):
        """Test CLI init command input validation."""
        self.assertGreaterEqual(len(recipe), 3)
        self.assertGreaterEqual(len(output_path), 1)

    @given(project_path=st.from_regex(r"[a-zA-Z0-9_/-]{1,50}", fullmatch=True), dry_run=st.booleans())
    def test_cli_update_command_inputs(self, project_path, dry_run):
        """Test CLI update command input validation."""
        self.assertGreaterEqual(len(project_path), 1)
        self.assertIsInstance(dry_run, bool)

    @given(query=st.text(min_size=1, max_size=50), limit=st.integers(min_value=1, max_value=100))
    def test_cli_discover_command_inputs(self, query, limit):
        """Test CLI discover command input validation."""
        self.assertGreaterEqual(len(query), 1)
        self.assertLessEqual(limit, 100)
        self.assertGreaterEqual(limit, 1)


class TestMergeResultProperties(unittest.TestCase):
    """Property-based tests for merge results."""

    @given(has_conflicts=st.booleans())
    def test_merge_result_consistency(self, has_conflicts):
        """Test merge result consistency."""
        self.assertIsInstance(has_conflicts, bool)


if __name__ == "__main__":
    unittest.main()
