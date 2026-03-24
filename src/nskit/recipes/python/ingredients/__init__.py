"""Ingredients for repos."""
from nskit.mixer import File, Folder
from nskit.recipes.python.ingredients import tools  # noqa: F401
from nskit.recipes.python.ingredients import docs  # noqa: F401

test_version = """from {{repo.py_name}} import __version__


def test_version():
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0
"""

test_dir = Folder(
    name='tests',
    contents=[
        Folder(
            name='unit',
            contents=[
                File(
                    name='test__version.py',
                    content=test_version
                )
            ]
        ),
        Folder(
            name='functional',
            contents=[
                File(name='.git-keep', content="")
            ]
        ),
        Folder(
            name='integration',
            contents=[
                File(name='.git-keep', content="")
            ]
        ),
        Folder(
            name='performance',
            contents=[
                File(name='.git-keep', content="")
            ]
        ),
        Folder(
            name='smoke',
            contents=[
                File(name='.git-keep', content="")
            ]
        )
    ]
)

src_dir = Folder(
    name='src',
    contents=[
        Folder(
            id_='src_path',
            name='{{repo.src_path}}',  # Make it be parsed as a template string for the name
            contents=[
                File(name='__init__.py', content='nskit.recipes.python.ingredients:__init__.py.jinja'),
                File(name='_version.py', content='nskit.recipes.python.ingredients:_version.py.jinja'),
            ]
        )
    ]
)
