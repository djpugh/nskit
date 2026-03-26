"""API Service Recipe."""

from typing import Union

from pydantic import Field

from nskit.mixer import File, Folder, LicenseFile
from nskit.recipes.python import PyRecipe, ingredients
from nskit.recipes.python.ingredients import api as api_ingredients


class APIRecipe(PyRecipe):
    """API Service Recipe."""

    contents: list[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            api_ingredients.pyproject_toml,
            api_ingredients.readme_md,
            ingredients.test_dir,
            api_ingredients.src_dir,
            api_ingredients.docker.docker_ignore,
            api_ingredients.docker.dockerfile,
            ingredients.docs_dir,
            LicenseFile(),
        ],
        description="The folder contents",
    )
