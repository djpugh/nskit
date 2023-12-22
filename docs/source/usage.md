# Using NSKit

## Installing
Installation is as simple as:
```
pip install nskit
```
It requires a Python version after 3.8+

### Optional dependencies

nskit has optional dependencies for different VCS systems:

* [Github](https://github.com) - add ``ghapi`` or use ``pip install nskit[github]``
* [Azure Devops](https://dev.azure.com) - add ``azure-cli`` or use ``pip install nskit[azure_devops]``

## Simple Usage

``nskit`` is designed to be used for two main use cases, creating repositories from repository recipes, and managing codebase repositories in a version control system.

### Creating a repo from a recipe

Recipes are the combination of ingredients (e.g. [nskit.recipes.python.ingredients][]) that are put together to create a template repository that can have contextual information added.

It uses [jinja2](https://jinja.palletsprojects.com/en/3.1.x/) to provide the template information.

There are 3 recipes provided through ``nskit``:

* [recipe][nskit.recipes.recipe.RecipeRecipe] for creating new recipes
* [python_package][nskit.recipes.python.package.PackageRecipe] for python packages
* [python_api_service][nskit.recipes.python.api.APIRecipe] for python [fastapi](https://fastapi.tiangolo.com) based  API services

A Recipe can be loaded and instantiated using the base [nskit.mixer.Recipe][] class
```
from nskit.mixer import Recipe
# kwargs are the context variables
# You can see the required and available fields/objects using
# print(Recipe.inspect(‘python_package))
# In this case, they are:

<Signature (*,
  name: str = ‘my_package’,
  repo: nskit.recipes.python.PyRepoMetadata = <Signature (*
    repo_separator: str = '-',
    owner: str,
    email:str,
    description: str = '',
    url: ...) -> nskit.recipes.python.PyRepoMetadata>,
  git: nskit.mixer.repo.GitConfig = <Signature (*,
    initial_branch_name: str = 'main',
    git_flow: bool = True) -> nskit.mixer.repo.GitConfig>,
  license: Optional[nskit.mixer.components.license_file.LicenseOptionsEnum] = None
) -> nskit.recipes.pythong.package.PackageRecipe>
# So to load it you have to specify the following fields
kwargs = {
    'repo': {
        'owner': ...,
        'email': ...,
        'url': ...
    }
}
# Although you can obviously override the defaults and set e.g. name, repo.description
my_package = Recipe.load(‘python_package’, **kwargs)
```

This uses entry points, specifically the ``nskit.recipes`` entrypoint to find other recipes.


And then create the recipe object:
```
my_package.create()
# creates the repository using the local directory as the root
# e.g. if it is creating a folder my_package it will be in <cwd>/my_package.

#The location and folder name can be customised:
my_package.create(base_path=‘/path/to/my/root/folder’, override_path=‘xyz’)
# Creates the template at /path/to/my/root/folder/xyz instead of <cwd>/my_package
# You could also specifically override context parameters at create time as additional kwargs
```

#### License Files

The 3 example templates have a license file option, using the [nskit.mixer.components.LicenseFile][] class, which calls the github API to get the license file definitions available on Github. These files will only be created if an appropriate ``license`` context variable is passed in (the default is None), so you can override the license with your own specific license in a template as required.

The license options are defined in [nskit.mixer.components.LicenseOptionsEnum][].

### Creating a codebase

The [nskit.vcs.Codebase][nskit.vcs] object is used to manage recipes on a remote version control system.

The supported providers with ``nskit`` are:

* [Github](https://www.github.com)
* [Azure Devops](https://dev.azure.com)

More can be added as extensions with the ``nskit.vcs.providers`` entry point (see [Extending nskit][]).

You need to initialise the codebase at the root folder that you want the codebase to exist under, or override the root_dir parameter.

I.e.

if you create a Codebase object as
```
c = Codebase()
```
It will use the current directory as the root directory.

Alternatively, you can specify the root directory
```
c = Codebase(root_dir=Path.cwd().parent)
```
To use the parent directory

There are other parameters that you can set:

* ``settings``: the codebase settings, configures the provider to use
* ``namespaces_dir``: the directory (from ``root_dir``) for the namespace constraints to be cloned to - see [Using namespaces][using-namespaces] below
* ``virtualenv_dir``: the directory (from ``root_dir``) for the virtualenv to be created in.
* ``virtualenv_args``: additional args to use for virtual env creation (e.g. azure_devops_artifacts_helpers)

The defaults for these should work, but can also be set via environment variables (or ``.env`` files).

The settings provide the provider to use.
This can be set through environment variables or .env files, and can either be set explicitly (via the ``vcs_provider`` settings parameter), or if that is not set, by trying to initialise all available providers to see if one succeeds - the last successful provider will be used.

Initialising the provider clients relies on the correct settings for that provider being set.

##### For Azure DevOps - [nskit.vcs.providers.azure_devops.AzureDevOpsSettings][]:

* ``organisation`` - the Azure Devops organisation to use
* ``project`` - the Azure Devops project to use

The azure devops url can also be overwritten for e.g private servers, although the associated API functionality is built against the cloud API.

These can be set using the following environment variables ``AZURE_DEVOPS_ORGANISATION``, and ``AZURE_DEVOPS_PROJECT``.

You may also want to set the ``NSKIT_PYTHON_INSTALLER_VIRTUALENV_ARGS`` environment variable to ``["--seeder","azdo-pip"]`` to make the created virtualenvironment be seeded with the azure devops authentication helpers. This is using pydantic settings handling, which parses environment variables for complex parameters as a JSON string.

!!! info

    This uses the [``azure_devops_artifacts_helpers``](https://djpugh.github.io/azure_devops_artifacts_helpers) library.

##### For Github - [nskit.vcs.providers.github.GithubSettings][]:

* ``organisation`` - the Github organisation/user to use
* ``token`` - the Github token to use

The github url can also be overwritten for e.g private servers, although the associated API functionality is built against the cloud API.

These can be set using the following environment variables ``GITHUB_ORGANISATION``, and ``GITHUB_TOKEN``.

There are other parameters that can be set for these providers as well as described in the [API][nskit.vcs.providers]

#### Creating a new repo

Once you have created a Codebase object, you can create a new repo using it.
```
c.create_repo('my_new_repo')
```

This will create the repo in the VCS provider (if it doesn't exist, erroring if it exists remotely or locally), and clone it to the local structure.

##### With a recipe

To use a recipe, you need to specify the recipe and kwargs in the ``create_repo`` call:
```
kwargs = {
    repo': {
        'owner': ...,
        'email': ...,
        'url': ...
    }
}
c.create_repo('my_new_package', with_recipe='python_package', **kwargs)
```
These are the same recipe names and kwargs as used in [Creating a repo from a recipe][creating-a-repo-from-a-recipe].

This will create that repo in the VCS and locally, and then use the recipe to initialise the repo with an intial commit, push it, and install into the virtualenv.

#### Cloning the codebase

You can use the codebase object to clone all the repos (see [Using namespaces][using-namespaces] for how this works with namespaces).

```
c.clone()
```

This will clone the repos in the VCS provider to the local directory, and install them into the virtualenv without dependencies, and then run through all the repos to install them with dependencies.

This means that you will get a virtualenv with all your codebase dependencies installed as editable installs.

## Advanced Usage
### Creating new recipes

A key feature from using ``nskit`` is the recipes. These can be added based on your personal or organisational needs.

The recipe approach is inspired by [cookiecutter](https://cookiecutter.readthedocs.io/), but is structured with a bottom up, building blocks, design, which allows easier inheritance and sharing of strutures and components.

There is an easy way to create a new recipe, using the [recipe][nskit.recipes.recipe.RecipeRecipe] recipe.

This will create a simple structure with the correct ``pyproject.toml``, including the ``[project.entry-points."nskit.recipes"]`` entrypoint section, and some template files.

There are 3 key parts to a recipe:

#### Ingredients
These are the recipe building blocks, intended to be template files and folders (e.g. a ``docs`` folder, or a ``src`` folder, or a ``.gitgnore`` file).

These use [jinja2](https://jinja.palletsprojects.com/en/3.1.x/) to provide the template information, and are built with two main python classes:

* [File][nskit.mixer.components.File] - has ``content`` which is either a ``jinja2`` template, callable, or just text, and a ``name``, which is again either a ``jinja2`` template, callable or text.
* [Folder][nskit.mixer.components.Folder] - has ``contents`` which is either [Files][nskit.mixer.components.File], or [Folders][nskit.mixer.components.Folder] and a ``name``, which is again either a ``jinja2`` template, callable, or text.

The callable options for ``content`` and ``name`` need to have the signature: ``def <func>(context: Dict[str, Any]):``. An example of these is the methods in [nskit.mixer.components.LicenseFile][] for the name and content ([get_license_filename][nskit.mixer.components.license_file.get_license_filename], and [get_license_content][nskit.mixer.components.license_file.get_license_content]).

These allow the different template blocks to be reused, and adapted.

Folder contents can be updated using indexing, either by ``name``, or ``id_`` (an additional parameter that can be set on  [Files][nskit.mixer.components.File] and [Folders][nskit.mixer.components.Folder] to allow for indexing), using e.g.:
```
my_folder = Folder(name='my_folder', contents = [
    File(name='example.md', id_='example', content='123')
])
my_new_file = File(name='example.md', content='Hello world')
# There are 3 ways to get the file in the folder:
# By list index
original_file = my_folder.contents[0]
# By name
original_file = my_folder['example.md']
# By id
original_file = my_folder['example']

# Each of those three ways can be used to also change it, e.g.
# my_folder.contents[0] = my_new_file
# my_folder['example.md'] = my_new_file
my_folder['example'] = my_new_file

# Note, because id_ is not set on my_new_file, referencing by the ID won't work now
```

!!! warning

    names and ids are not enorced to be unique, so the first response that matches either id or name is returned. If you anticipate making use of this, please make sure files and ids do not clash

#### Hooks

A [Hook][nskit.mixer.components.Hook] is a callable object that can modify things before or after the recipe is created.

These are intended for e.g. specific configuration actions, or installing/configuring utilities (e.g. ``pre-commit``).

Hooks are easy to create, see for example the code for the [nskit.mixer.hooks.git.GitInit] hook, or for a more simple example:
```
from typing import Any, Dict
from pathlib import Path

from nskit.mixer.components import Hook

class MyHook(Hook):

    def call(self, recipe_path: Path, context: Dict[str, Any]):
        """This is where your hook logic goes"""
        # recipe_path is the proposed (if pre_hook) path to create the recipe at,
        # or current (if post_hook) path the recipe has been created at.
        #
        # context is the proposed (if pre_hook) context dictionary to pass to the templates,
        # or used context dictionary (if post_hook)
        #
        print(f'Recipe created at {recipe_path}, with context {context}')
        # return None
        # or
        # return recipe_path, context
        # e.g. if you edit them/change them
```

#### Recipe

The [Recipe][nskit.mixer.components.Recipe] is the main object that pulls this all together. It inherits from [Folder][nskit.mixer.components.Folder], and adds the ``pre_hooks`` and ``post_hooks`` variables.

When creating a recipe, you should add fields (the [Folder][nskit.mixer.components.Folder] object is based on [pydantic](https://pydantic-docs.helpmanual.io/)) for context variables as required.

There is a more specific [CodeRecipe][nskit.mixer.repo.CodeRecipe] class which includes repo metadata, git configuration, and git initialisation and precommit install hooks, that is recommended for creating recipes that are code repositories.

A good example recipe is [nskit.recipes.python.api.APIRecipe][], which includes inheritance from  [nskit.recipes.python.package.PackageRecipe][] (inheriting from a python base recipe [nskit.recipes.python.PyRecipe][]).

For a more simple example for a general repo:
```
from typing import List, Union
from nskit.mixer import CodeRecipe, File, Folder

class MyRecipe(CodeRecipe):
    contents: List[Union[File, Folder]] = [
        Folder(name='my_recipe', contents=[
            File(name='hello_world.txt', content='Hello world! from {{whoami}}')
        ])
    ]
    # Adding a simple context variable
    whoami: str
    # This doesn't have a default so needs to be set when initialising the repo
    # You could e.g. use pydantic validators or Field factories to initialise this dynamically as well
```

To make a recipe available to ``nskit``, you need to make it an installable entrypoint, e.g. in ``pyproject.toml``:
```
[project.entry-points."nskit.recipes"]
my_recipe = "my_package.my_recipe:MyRecipe"
```

and, when installed in the environment with nskit, will be available as ``my_recipe`` using the commands described in [Creating a repo from a recipe][]

### Recipes in other languages

It is possible to create additional installation handlers for other languages. This uses the ``nskit.vcs.installers`` entrypoint, and should inherit from [nskit.vcs.installer.Installer][].

This has two abstract methods that should be implemented for a specific language:

* ``check_repo`` - check if the repo is of the language/installer type
* ``install`` - takes the repo path, current codebase (optional), and whether to install dependencies (``deps``) and gets the appropriate installation environment from the codebase or elsewhere.

An example of this is the [nskit.vcs.installer.PythonInstaller][].

This implements editable python package installation into a ``virtualenv`` in the codebase root. It has some specific configuration variables (that can be set using environment variables:

* ``NSKIT_PYTHON_INSTALLER_ENABLED`` - set to false to disable
* ``NSKIT_PYTHON_INSTALLER_VIRTUALENV_DIR`` - set a specific directory path, or directory name for the virtualenv dir to use
*  ``NSKIT_PYTHON_INSTALLER_VIRTUALENV_ARGS`` - specify any specific args for virtualenv.

And provides the two methods mentioned above:
* ``check_repo`` - checks if there is a ``setup.py``, ``pyproject.toml``, or ``requirements.txt`` file in the repo root
* ``install`` - gets the virtualenv/other executable to use and installs with/without dependencies as configured.

A similar installer can be implemented for other languages (using e.g. ``subprocess`` for running the installation).

!!! note
    To set the environment variable names, use the ``model_config`` variable:
    ```
        model_config = SettingsConfigDic(env_prefix='<MY_ENV_PREFIX_>', env_file='.env')

    ```

!!! warning

    All installers will be tried, and if they are enabled (using environment variables), and the repo passes the ``check_repo`` call, the install method will be called. This could cause issues for multi-language repos. For complex cases like that, we suggest using a custom installer and disabling the others.

### Using namespaces

Another key feature of ``nskit`` is handling namespaces. A namespace is e.g. a organisational or personal naming convention that makes it easy to identify and structure repositories and modules.

For python code, this might look like ``my_org.my_team.my_module``, but can look different for other languages.
You may want to replicate this in my repository naming convention (which doesn't usually allow folders in repository names), and this can be done with the [nskit.vcs.NamespaceValidationRepo][nskit.vcs], which can be created and stored in your VCS.

The structure of the namespace file is a ``namespace.yaml`` file with valid names at a given level, e.g.:
```
options;
- my_org:
    - my_team
    - team_a:
        - module_1
        - module_2
```
Which means we can have repos structured as:
```
my_org-my_team-<*>
my_org-team_a-module_1
my_org-team_a-module_1-<*>
my_org-team_a-module_2
my_org-team_a-module_2-<*>
```
But no others.

You can create a namespace repo for a codebase:

```
from nskit.vcs import Codebase

c = Codebase()
options = [{'my_org': ['my_team', {'team_a': ['module_1', 'module_2']}]}]
c.create_namespace_repo(namespace_options=options)
```

There are additional parameters that you can set:

* ``repo_separator`` defines the separator to use on the VCS repo names (defaults to ``-``)
* ``delimiters`` is a list of valid delimiters to use to split the names up (defaults to a standard set of ``,``, ``.``, ``-``)

You will also need to set the validation level to ensure name validation occurs when creating new repos.

```
c.settings.validation_level =  c.settings.validation_level.strict
# Options are none (default), warning, and strict
```
With strict validation and a ``namespace_validation_repo`` for the codebase, creating a repo with a non-matching name will error (otherwise it will just warn, or do nothing)
```
c.create_repo(name='abc-def')
# Raise a ValueError
```

If you are not using the full codebase behaviours, you can also set the ``namespace_validation_repo`` parameter on the [nskit.vcs.repo.Repo][] object to enforce name validation.

### Inheriting

``nskit`` is designed to be used as a based for creating your own scaffolding for managing an organisational or personal codebase with namespaces.

You can provide simple stubs in your own module/package for a few key classes:

* [nskit.vcs.Codebase][]
* [nskit.mixer.CodeRecipe][]
* [nskit.mixer.Recipe][]
* [nskit.mixer.File][]
* [nskit.mixer.Folder][]

which make it easy for people to refer to that (and add customisation, and e.g. additional extensions or recipes as required) for your internal use.

### Extending nskit

``nskit`` is designed around a few key entrypoints to make it easily accessible, including

- ``[project.entry-points."nskit.recipes"]`` for code recipes
- ``[project.entry-points."nskit.vcs.providers"]`` for other VCS providers
- ``[project.entry-points."nskit.mixer.environment.extensions"]`` for the mixer ``jinja2`` [Environment][jinja2.Environment] extensions
- ``[project.entry-points."nskit.mixer.environment.factory"]`` for the mixer ``jinja2`` [Environment][jinja2.Environment] initialisation

Additionally, key methods and behaviours can be overwritten or extended using inheritance.

#### Customising the ``nskit.mixer`` ``jinja2`` ``Environment``

There are 2 entrypoints to enable customising the Jinja Environment used for the template rendering.

- ``[project.entry-points."nskit.mixer.environment.extensions"]`` for the mixer ``jinja2`` [Environment][jinja2.Environment] extensions
- ``[project.entry-points."nskit.mixer.environment.factory"]`` for the mixer ``jinja2`` [Environment][jinja2.Environment] initialisation

The first allows extension recipes to define a list of extensions to add to the environment (must be installed as dependencies of the recipe)

An example might be:
```
def recipe_jinja_extensions():
    return ['jinja2.ext.debug', 'jinja2.ext.i8n']
```

This could be implemented as a staticmethod on the recipe object or similar, but it needs to be defined to the ``nskit.mixer.environment.extensions`` entrypoint in the ``pyproject.toml``.

!!! warning

    All requested extensions for installed recipes are added to the environment so it could be possible for clashes/issues to occur there, however given the maturity of the jinja ecosystem, we are not loading them recipe by recipe due to the added complexity/issues.

You can also customise the environment initialisation if you need to override specifics of the configuration however this is not recommended as it can cause complex issues with the templates/handling.

The default implementation defines the loader to use ``_PkgResourcesTemplateLoader`` to allow for package resources type loading on the environment (see examples above), but other parameters could be configured/changed by setting the ``NSKIT_MIXER_JINJA_ENVIRONMENT_FACTORY`` environment variable to the name of the entrypoint.

!!! warning

    The default configurations are the expected one, so changing this could break e.g. inherited ingredients, so proceed with caution.
