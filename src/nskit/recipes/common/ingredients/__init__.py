"""Shared Python ingredients for recipes."""
from nskit.mixer import File, Folder

pre_commit_config = File(
    name=".pre-commit-config.yaml",
    content="nskit.recipes.common.ingredients:pre_commit_config.yaml.jinja",
)

gitignore = File(
    name=".gitignore",
    content="nskit.recipes.common.ingredients:gitignore.jinja",
)

codeowners = File(
    name="CODEOWNERS",
    content="nskit.recipes.common.ingredients:codeowners.jinja",
)

# Taskfiles folder structure
taskfiles_folder = Folder(
    name="taskfiles",
    contents=[
        File(
            name="common.yml",
            content="nskit.recipes.common.ingredients:taskfiles_common.yml.jinja",
        ),
    ],
)

# Base Taskfile template
taskfile = File(
    name="Taskfile.yml",
    content="nskit.recipes.common.ingredients:Taskfile.yml.jinja",
)

# Base README template
readme_base = File(
    name="README.md",
    content="nskit.recipes.common.ingredients:README.md.jinja",
)
