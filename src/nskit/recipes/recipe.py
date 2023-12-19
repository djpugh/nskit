"""A Recipe for creating Recipes, meta!"""
from typing import List, Union

from pydantic import Field

from nskit.mixer import File, Folder, LicenseFile
from nskit.recipes.python import ingredients, PyRecipe
from nskit.recipes.python.ingredients import recipe as recipe_ingredients


class RecipeRecipe(PyRecipe):
    """A Recipe for creating Recipes, meta!"""

    contents: List[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            recipe_ingredients.pyproject_toml,
            recipe_ingredients.readme_md,
            ingredients.test_dir,
            recipe_ingredients.src_dir,
            ingredients.docs_dir,
            LicenseFile()
        ],
        description='The folder contents')
