"""Ingredients for repos."""
from nskit.mixer import File, Folder
from nskit.recipes.python.ingredients.docs import docs_dir  # noqa: F401

gitignore = File(
    name='.gitignore',
    content='nskit.recipes.python.ingredients:gitignore.template'
    )
noxfile = File(
    name='noxfile.py',
    content='nskit.recipes.python.ingredients:noxfile.py.template'
    )
pre_commit = File(
    name='.pre-commit-config.yaml',
    content='nskit.recipes.python.ingredients:pre-commit-config.yaml.template'
    )
pyproject_toml = File(
    name='pyproject.toml',
    content='nskit.recipes.python.ingredients:pyproject.toml.template'
    )
readme_md = File(
    name='README.md',
    content='nskit.recipes.python.ingredients:readme.md.template'
    )

test_placeholder = """import {{repo.py_name}}


def test_placeholder():
    pass
"""

test_dir = Folder(
    name='tests',
    contents=[
        Folder(
            name='unit',
            contents=[
                File(
                    name='test_placeholder.py',
                    content=test_placeholder
                )
            ]
        ),
        Folder(
            name='functional',
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
                File(name='__init__.py', content='nskit.recipes.python.ingredients:__init__.py.template')
            ]
        )
    ]
)
