"""Docker ingredients.

Contains dockerfile, .dockerignore files.
"""
from nskit.mixer import File

api_dockerfile = File(
    name='Dockerfile',
    content='nskit.recipes.python.ingredients.api.docker:api.Dockerfile.template'
    )
dockerignore = File(
    name='.dockerignore',
    content='nskit.recipes.python.ingredients.api.docker:dockerignore.template'
    )
