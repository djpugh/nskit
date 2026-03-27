"""Ingredients for repos."""

from nskit.mixer import File, Folder
from nskit.recipes.python.ingredients import (
    docs,  # noqa: F401
    tools,  # noqa: F401
)
from nskit.recipes.python.ingredients.docs import docs_dir  # noqa: F401
from nskit.recipes.python.ingredients.tools import (  # noqa: F401
    gitignore,
    noxfile,
    pre_commit,
    pyproject_toml,
    readme_md,
)

test_version = """from {{repo.py_name}} import __version__


def test_version():
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0
"""

_GIT_KEEP = ".git-keep"

test_dir = Folder(
    name="tests",
    contents=[
        Folder(name="unit", contents=[File(name="test__version.py", content=test_version)]),
        Folder(name="functional", contents=[File(name=_GIT_KEEP, content="")]),
        Folder(name="integration", contents=[File(name=_GIT_KEEP, content="")]),
        Folder(name="performance", contents=[File(name=_GIT_KEEP, content="")]),
        Folder(name="smoke", contents=[File(name=_GIT_KEEP, content="")]),
    ],
)

src_dir = Folder(
    name="src",
    contents=[
        Folder(
            id_="src_path",
            name="{{repo.src_path}}",  # Make it be parsed as a template string for the name
            contents=[
                File(name="__init__.py", content="nskit.recipes.python.ingredients.src:__init__.py.jinja"),
                File(name="_version.py", content='__version__ = "0.0.0"\n'),
            ],
        )
    ],
)
