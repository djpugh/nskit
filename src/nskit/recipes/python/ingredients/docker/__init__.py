
from nskit.mixer import File
from nskit.recipes.python.ingredients.tools import taskfiles_folder  # noqa: F401


taskfiles_folder.contents += [
    File(
        name='python-package.yml',
        content='nskit.recipes.python.ingredients.docker:taskfiles_docker.yml.jinja'
    )
]

taskfile = File(
    name='Taskfile.yml',
    content='nskit.recipes.python.ingredients.docker:Taskfile.yml.jinja'
)


dockerfile = File(
    name='Dockerfile',
    content='nskit.recipes.python.ingredients.docker:dockerfile.jinja'
)

docker_ignore = File(
    name='.dockerignore',
    content='nskit.recipes.python.ingredients.docker:docker_ignore.jinja'
)