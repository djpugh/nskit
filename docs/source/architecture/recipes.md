# Recipe Architecture

## The Composition Model

nskit recipes are not monolithic templates. They're assembled from small, reusable pieces called **ingredients** — individual files, folders, and Jinja2 templates — that can be shared, extended, and overridden.

```mermaid
graph TD
    subgraph "Shared Ingredients"
        GI[.gitignore]
        PT[pyproject.toml]
        RM[README.md]
        TD[test_dir/]
        SD[src_dir/]
        DD[docs_dir/]
    end

    subgraph "Python Package Recipe"
        GI --> PKG[PackageRecipe]
        PT --> PKG
        RM --> PKG
        TD --> PKG
        SD --> PKG
        DD --> PKG
    end

    subgraph "API Service Recipe"
        GI --> API[APIRecipe]
        PT2[pyproject.toml<br/><i>extended</i>] --> API
        RM2[README.md<br/><i>extended</i>] --> API
        TD --> API
        SD2[src_dir/<br/><i>+ app.py, server.py</i>] --> API
        DF[Dockerfile] --> API
        DD --> API
    end
```

### Ingredients Are Reusable

An ingredient is just a `File` or `Folder` instance. The same ingredient can appear in multiple recipes:

```python
# Shared ingredients
from nskit.recipes.python import ingredients

# Python package recipe — uses shared ingredients directly
class PackageRecipe(PyRecipe):
    contents = [
        ingredients.gitignore,
        ingredients.pyproject_toml,
        ingredients.readme_md,
        ingredients.test_dir,
        ingredients.src_dir,
        ingredients.docs_dir,
    ]

# API service recipe — same shared ingredients + extras
class APIRecipe(PyRecipe):
    contents = [
        ingredients.gitignore,
        api_ingredients.pyproject_toml,   # extended version
        api_ingredients.readme_md,        # extended version
        ingredients.test_dir,
        api_ingredients.src_dir,          # adds app.py, server.py
        docker_ingredients.dockerfile,    # API-specific
        docker_ingredients.docker_ignore, # API-specific
        ingredients.docs_dir,
    ]
```

When the shared `gitignore` ingredient improves, both recipes get the update.

### Templates Support Inheritance

Jinja2 template inheritance lets specialised recipes extend base templates without duplicating them:

```jinja
{# api/pyproject.toml.jinja — extends the base #}
{% extends "nskit.recipes.python.ingredients.tools:pyproject.toml.jinja" %}

{% block Dependencies %}
    {{ super() }}
    "fastapi",
    "uvicorn",
{% endblock Dependencies %}
```

The base `pyproject.toml.jinja` defines the full structure with extension blocks. The API version only overrides the dependencies block, inheriting everything else.

### Recipes Extend Recipes

Python class inheritance works naturally:

```python
class PyRecipe(CodeRecipe):
    """Base for all Python recipes — adds repo metadata, naming conventions."""
    repo: PyRepoMetadata = Field(...)

class PackageRecipe(PyRecipe):
    """Adds package-specific ingredients."""
    contents = [...]

class APIRecipe(PyRecipe):
    """Adds API-specific ingredients on top of the same base."""
    contents = [...]
```

### Ingredients Can Be Modified

Ingredients are Pydantic models, so they can be deep-copied and extended:

```python
# Start with the shared src_dir
src_dir = ingredients.src_dir.model_copy(deep=True)

# Add API-specific files to it
src_dir['src_path'].contents += [
    File(name='app.py', content='my_recipe:app.py.jinja'),
    File(name='server.py', content='my_recipe:server.py.jinja'),
]
```

This lets you build on shared structure without modifying the original.

## Recipe Lifecycle

```mermaid
graph LR
    DEF["1. Define<br/>Recipe class + ingredients"] --> REG["2. Register<br/>Python entry point"]
    REG --> DIST["3. Distribute<br/>Docker image or package"]
    DIST --> INIT["4. Initialise<br/>User generates project"]
    INIT --> CUST["5. Customise<br/>User modifies files"]
    CUST --> UPD["6. Update<br/>3-way merge"]
    UPD --> CUST
```

## Why This Matters for Organisations

A platform team can maintain:

- **Common ingredients** — CI pipelines, linting config, Docker templates, security policies
- **Language-specific bases** — Python package, Go service, Terraform module
- **Team-specific recipes** — Composed from common + language ingredients + team overrides

When a security policy changes, update the shared ingredient once. Every recipe that uses it picks up the change. Every project built from those recipes can adopt it via 3-way merge update.
