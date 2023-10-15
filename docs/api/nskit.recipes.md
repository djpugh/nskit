
::: nskit.recipes
    options:
        show_root_heading: False
        heading_level: 1

## ::: nskit.recipes.recipe.RecipeRecipe
    options:
        show_root_heading: True
        members:
            - contents

## ::: nskit.recipes.python.api.APIRecipe
    options:
        show_root_heading: True
        members:
            - contents

## ::: nskit.recipes.python.package.PackageRecipe
    options:
        show_root_heading: True
        members:
            - contents


## Python Ingredients

### ::: nskit.recipes.python.PyRecipe
    options:
        show_root_heading: True
        inherited_members: true
        members:
            - name
            - version
            - repo
            - pre_hooks
            - post_hooks
            - extension_name
            - git
            - context
            - recipe_batch
            - dryrun
            - validate
            - create
            - load


### ::: nskit.recipes.python.PyRepoMetadata
    options:
        show_root_heading: True
        inherited_members: true
        members:
            - repo_seprator
            - owner
            - email
            - descriptuon
            - url
            - name
            - py_name
            - py_root
            - src_path
            - module_depth

### ::: nskit.recipes.python.ingredients
    options:
        show_root_heading: True
        members:
            - gitignore
            - noxfile
            - pre_commit
            - pyproject_toml
            - readme_md
            - test_dir
            - src_dir


### ::: nskit.recipes.python.ingredients.api
    options:
        show_root_heading: True
        members:
            - pyproject_toml
            - readme_md

#### ``src_dir``

Adds ``app.py``, ``auth.py``, ``server.py``, ``api/__init__.py``, ``base.py`` to [nskit.recipes.python.ingredients.src_dir]

### ::: nskit.recipes.python.ingredients.api.docker
    options:
        show_root_heading: True
        members:
            - api_dockerfile
            - dockerignore

### ::: nskit.recipes.python.ingredients.recipe
    options:
        show_root_heading: True
        members:
            - pyproject_toml
            - readme_md

#### ``src_dir``
Adds ``recipe.py`` and ``ingredient.py.template`` to [nskit.recipes.python.ingredients.src_dir]
