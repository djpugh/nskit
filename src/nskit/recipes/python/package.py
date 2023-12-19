"""Package Recipe."""
from typing import List, Union

from pydantic import Field

from nskit.mixer import File, Folder, LicenseFile
from nskit.recipes.python import ingredients, PyRecipe


class PackageRecipe(PyRecipe):
    """Package Recipe."""

    contents: List[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            ingredients.pyproject_toml,
            ingredients.readme_md,
            ingredients.test_dir,
            ingredients.src_dir,
            ingredients.docs_dir,
            LicenseFile()
        ],
        description='The folder contents')
