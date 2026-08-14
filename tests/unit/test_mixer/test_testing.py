"""Tests for the reusable recipe test harness (nskit.mixer.testing)."""

import unittest

from nskit.mixer.testing import check_recipe, check_recipes, list_recipes

_REPO = {
    "owner": "Joe Bloggs",
    "email": "joe.bloggs@test.com",
    "description": "Test",
    "url": "https://www.test.com",
}


class TestMixerTesting(unittest.TestCase):
    """Tests for nskit.mixer.testing utilities."""

    def test_list_recipes_includes_builtins(self):
        names = list_recipes()
        self.assertIn("python_package", names)
        self.assertEqual(names, sorted(names))

    def test_check_recipe_passes_for_builtin(self):
        result = check_recipe("python_package", {"name": "test_package", "repo": _REPO})
        self.assertTrue(result.ok, result.summary())
        self.assertGreater(result.file_count, 0)
        self.assertFalse(result.unresolved_resources)
        self.assertFalse(result.template_errors)
        self.assertFalse(result.duplicate_paths)

    def test_check_recipe_reports_construction_error_on_bad_inputs(self):
        # Missing required ``repo`` -> construction fails, reported not raised.
        result = check_recipe("python_package", {"name": "test_package"})
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.construction_error)

    def test_check_recipes_flags_registered_recipe_without_inputs(self):
        # Only supply inputs for one of the registered recipes.
        results = check_recipes({"python_package": {"name": "test_package", "repo": _REPO}})
        # Every other registered recipe should be reported as missing inputs.
        untested = [
            name for name, r in results.items() if r.construction_error and "no sample inputs" in r.construction_error
        ]
        self.assertEqual(set(untested), set(list_recipes()) - {"python_package"})

    def test_check_recipe_accepts_class_and_instance(self):
        from nskit.recipes.python.package import PackageRecipe

        by_class = check_recipe(PackageRecipe, {"name": "test_package", "repo": _REPO})
        self.assertTrue(by_class.ok, by_class.summary())

        instance = PackageRecipe(name="test_package", repo=_REPO)
        by_instance = check_recipe(instance)
        self.assertTrue(by_instance.ok, by_instance.summary())


if __name__ == "__main__":
    unittest.main()
