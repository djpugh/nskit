from nskit.mixer import File, Folder
from nskit.recipes.python.ingredients.tools import taskfiles_folder  # noqa: F401

taskfiles_folder.contents += [
    File(
        name="python-package.yml", content="nskit.recipes.python.ingredients.package:taskfiles.python_package.yml.jinja"
    )
]

taskfile = File(name="Taskfile.yml", content="nskit.recipes.python.ingredients.package:Taskfile.yml.jinja")
