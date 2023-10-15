"""Ingredients for a recipe recipe."""
from nskit.mixer import File
from nskit.recipes.python.ingredients import src_dir as _src_dir

pyproject_toml = File(
    name='pyproject.toml',
    content='nskit.recipes.python.ingredients.recipe:pyproject.toml.template'
    )

readme_md = File(
    name='README.md',
    content='nskit.recipes.python.ingredients.recipe:readme.md.template'
    )


src_dir = _src_dir.model_copy(deep=True)
src_dir['src_path'].contents += [
    File(
        name='recipe.py',
        content='nskit.recipes.python.ingredients.recipe:recipe.py.template'
        ),
    File(
        name='ingredient.py.template',
        content='nskit.recipes.python.ingredients.recipe:ingredient.py.template.template'
        )
]
