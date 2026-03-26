"""Ingredients for a recipe recipe."""

from nskit.mixer import File
from nskit.recipes.python.ingredients import src_dir as _src_dir
from nskit.recipes.python.ingredients.docker import docker_ignore

pyproject_toml = File(name="pyproject.toml", content="nskit.recipes.python.ingredients.recipe:pyproject.toml.jinja")

readme_md = File(name="README.md", content="nskit.recipes.python.ingredients.recipe:readme.md.jinja")

dockerfile = File(name="Dockerfile", content="nskit.recipes.python.ingredients.recipe:Dockerfile.jinja")


src_dir = _src_dir.model_copy(deep=True)
src_dir["src_path"].contents += [
    File(name="recipe.py", content="nskit.recipes.python.ingredients.recipe:recipe.py.jinja"),
    File(name="ingredient.py.jinja", content="nskit.recipes.python.ingredients.recipe:ingredient.py.jinja.jinja"),
]


# What build info to use here (docker?)
