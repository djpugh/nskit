"""API Service ingredients.

Contains fastapi based api service ingredients.
"""
from nskit.mixer import File, Folder
from . import docker
from .. import src_dir as _src_dir

pyproject_toml = File(
    name='pyproject.toml',
    content='nskit.recipes.python.ingredients.api:pyproject.toml.template'
    )

readme_md = File(
    name='README.md',
    content='nskit.recipes.python.ingredients.api:readme.md.template'
    )


src_dir = _src_dir.model_copy(deep=True)
src_dir['src_path'] += [
    File(
        name='app.py',
        content='nskit.recipes.python.ingredients.api:app.py.template'
        ),
    File(
        name='auth.py',
        content='nskit.recipes.python.ingredients.api:auth.py.template'
        ),
    File(
        name='server.py',
        content='nskit.recipes.python.ingredients.api:server.py.template'
        ),
    Folder(
        name='api',
        contents=[
            File(
                name='__init__.py',
                content='nskit.recipes.python.ingredients.api:api.__init__.py.template'
            ),
            File(
                name='base.py',
                content='nskit.recipes.python.ingredients.api:api.base.py.template'
            )
        ]
    )
]
