"""API Service ingredients.

Contains fastapi based api service ingredients.
"""

from nskit.mixer import File, Folder
from nskit.recipes.python.ingredients import docker  # noqa: F401
from nskit.recipes.python.ingredients import src_dir as _src_dir

pyproject_toml = File(name="pyproject.toml", content="nskit.recipes.python.ingredients.api:pyproject.toml.jinja")

readme_md = File(name="README.md", content="nskit.recipes.python.ingredients.api:README.md.jinja")


src_dir = _src_dir.model_copy(deep=True)
src_dir["src_path"].contents += [
    File(name="app.py", content="nskit.recipes.python.ingredients.api:app.py.jinja"),
    File(name="server.py", content="nskit.recipes.python.ingredients.api:server.py.jinja"),
    Folder(
        name="api",
        contents=[
            File(name="__init__.py", content="nskit.recipes.python.ingredients.api:api.__init__.py.jinja"),
            File(name="base.py", content="nskit.recipes.python.ingredients.api:api.base.py.jinja"),
        ],
    ),
]
