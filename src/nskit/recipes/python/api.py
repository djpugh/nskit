"""API Service Recipe."""
from typing import List, Union

from pydantic import Field

from nskit.mixer import File, Folder, LicenseFile
from nskit.recipes.python import ingredients, PyRecipe
from nskit.recipes.python.ingredients import api as api_ingredients


class APIRecipe(PyRecipe):
    """API Service Recipe."""

    contents: List[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            api_ingredients.pyproject_toml,
            api_ingredients.readme_md,
            ingredients.test_dir,
            api_ingredients.src_dir,
            api_ingredients.docker.dockerignore,
            api_ingredients.docker.api_dockerfile,
            ingredients.docs_dir,
            LicenseFile()
        ],
        description='The folder contents')
