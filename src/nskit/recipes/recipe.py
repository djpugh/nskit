"""A Recipe for creating Recipes, meta!"""

from typing import Union

from pydantic import Field

from nskit.mixer import File, Folder, LicenseFile
from nskit.mixer.components.recipe import RECIPE_ENTRYPOINT
from nskit.recipes.python import PyRecipe, ingredients
from nskit.recipes.python.ingredients import recipe as recipe_ingredients


class RecipeRecipe(PyRecipe):
    """A Recipe for creating Recipes, meta!"""

    recipe_entrypoint: str = RECIPE_ENTRYPOINT
    contents: list[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            recipe_ingredients.pyproject_toml,
            recipe_ingredients.readme_md,
            recipe_ingredients.dockerfile,
            recipe_ingredients.docker_ignore,
            ingredients.test_dir,
            recipe_ingredients.src_dir,
            ingredients.docs_dir,
            LicenseFile(),
        ],
        description="The folder contents",
    )
