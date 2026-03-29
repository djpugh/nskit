"""MKDocs templates."""

from nskit.mixer import File, Folder

docs_dir = Folder(
    name="docs",
    contents=[
        Folder(
            name="source",
            contents=[
                File(name="index.md", content="nskit.recipes.python.ingredients.docs:index.md.jinja"),
                File(name="usage.md", content="nskit.recipes.python.ingredients.docs:usage.md.jinja"),
                Folder(
                    name="developing",
                    contents=[
                        File(
                            name="index.md", content="nskit.recipes.python.ingredients.docs:developing_index.md.jinja"
                        ),
                        File(name="license.md", content="nskit.recipes.python.ingredients.docs:license.md.jinja"),
                    ],
                ),
            ],
        ),
        File(name="mkdocs.yml", content="nskit.recipes.python.ingredients.docs:mkdocs.yml.jinja"),
    ],
)
