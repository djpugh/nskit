"""Ingredients for repos."""
from nskit.mixer import File, Folder
from nskit.recipes.common.ingredients import taskfiles_folder  # noqa: F401

gitignore = File(name=".gitignore", content="nskit.recipes.python.ingredients.tools:gitignore.jinja")
noxfile = File(name="noxfile.py", content="nskit.recipes.python.ingredients.tools:noxfile.py.jinja")
pre_commit = File(
    name=".pre-commit-config.yaml", content="nskit.recipes.python.ingredients.tools:pre-commit-config.yaml.jinja"
)
pyproject_toml = File(name="pyproject.toml", content="nskit.recipes.python.ingredients.tools:pyproject.toml.jinja")
readme_md = File(name="README.md", content="nskit.recipes.python.ingredients.tools:readme.md.jinja")

taskfiles_folder = taskfiles_folder.model_copy()

taskfiles_folder.contents += [
    File(name="python-common.yml", content="nskit.recipes.python.ingredients.tools:taskfiles.python_common.yml.jinja")
]

taskfile = File(name="Taskfile.yml", content="nskit.recipes.python.ingredients.tools:Taskfile.yml.jinja")
