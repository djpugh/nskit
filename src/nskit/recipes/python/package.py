from typing import List, Union

from pydantic import Field

from nskit.mixer import File, Folder
from nskit.recipes.python import ingredients, PyRecipe


class PackageRecipe(PyRecipe):

    contents: List[Union[File, Folder]] = Field(
        [
            ingredients.gitignore,
            ingredients.noxfile,
            ingredients.pre_commit,
            ingredients.pyproject_toml,
            ingredients.readme_md,
            ingredients.test_dir,
            ingredients.src_dir
        ],
        description='The folder contents')