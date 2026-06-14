"""Tests for the reusable recipe test harness (nskit.mixer.testing)."""

from nskit.mixer.testing import check_recipe, check_recipes, list_recipes

_REPO = {
    "owner": "Joe Bloggs",
    "email": "joe.bloggs@test.com",
    "description": "Test",
    "url": "https://www.test.com",
}


def test_list_recipes_includes_builtins():
    names = list_recipes()
    assert "python_package" in names
    assert names == sorted(names)


def test_check_recipe_passes_for_builtin():
    result = check_recipe("python_package", {"name": "test_package", "repo": _REPO})
    assert result.ok, result.summary()
    assert result.file_count > 0
    assert not result.unresolved_resources
    assert not result.template_errors
    assert not result.duplicate_paths


def test_check_recipe_reports_construction_error_on_bad_inputs():
    # Missing required ``repo`` -> construction fails, reported not raised.
    result = check_recipe("python_package", {"name": "test_package"})
    assert not result.ok
    assert result.construction_error is not None


def test_check_recipes_flags_registered_recipe_without_inputs():
    # Only supply inputs for one of the registered recipes.
    results = check_recipes({"python_package": {"name": "test_package", "repo": _REPO}})
    # Every other registered recipe should be reported as missing inputs.
    untested = [
        name for name, r in results.items() if r.construction_error and "no sample inputs" in r.construction_error
    ]
    assert set(untested) == set(list_recipes()) - {"python_package"}


def test_check_recipe_accepts_class_and_instance():
    from nskit.recipes.python.package import PackageRecipe

    by_class = check_recipe(PackageRecipe, {"name": "test_package", "repo": _REPO})
    assert by_class.ok, by_class.summary()

    instance = PackageRecipe(name="test_package", repo=_REPO)
    by_instance = check_recipe(instance)
    assert by_instance.ok, by_instance.summary()
