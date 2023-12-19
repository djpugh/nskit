"""MKDocs templates."""
from nskit.mixer import File, Folder

docs_dir = Folder(name='docs', contents=[
    Folder(name='source', contents=[
        File(name='index.md', content='nskit.recipes.python.ingredients.docs:index.md.template'),
        File(name='usage.md', content='nskit.recipes.python.ingredients.docs:usage.md.template'),
        Folder(name='developing', contents=[
            File(name='index.md', content='nskit.recipes.python.ingredients.docs:developing_index.md.template'),
            File(name='license.md', content='nskit.recipes.python.ingredients.docs:license.md.template')

        ]),
    ]),
    File(name='mkdocs.yml', content='nskit.recipes.python.ingredients.docs:mkdocs.yml.template')
])
