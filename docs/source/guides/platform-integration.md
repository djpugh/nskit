# Platform Integration

This guide is for platform engineers setting up nskit for an organisation. It covers the three things you need to configure, and how to wrap them in a CLI.

## The Three Things to Configure

### 1. Backend (Required)

The backend tells nskit where recipes live and how to execute them. It drives the engine:

- **No backend (default):** Recipes discovered from installed packages, executed locally. Not recommended for production — no versioning, no reproducible updates.
- **`GitHubBackend`:** Discovers recipes from GitHub repos/releases, executes via Docker images from ghcr.io.
- **`DockerBackend`:** Discovers from a Docker registry, executes via Docker.
- **`LocalBackend`:** Discovers from a local directory. Useful for development.

```python
from nskit.client.backends import GitHubBackend

backend = GitHubBackend(
    org='myorg',                              # GitHub org
    repo_pattern='{recipe_name}',             # Repo name pattern
    entrypoint='mycompany.recipes',           # Entry point group
)
```

The backend also controls what `nskit list` shows — with a `GitHubBackend`, it lists repos and their release tags. With a `DockerBackend`, it lists images and tags. Without a backend, it falls back to locally installed entry points.

### 2. Entry Point Group (Required for Local Mode)

The entry point group name determines which recipes are discoverable when running locally (without Docker). It must match between your recipe packages and the CLI configuration:

```toml
# In recipe package's pyproject.toml
[project.entry-points."mycompany.recipes"]
python_package = "mycompany.recipes:PackageRecipe"
```

```python
# In CLI setup
app = create_cli(
    recipe_entrypoint='mycompany.recipes',  # Must match
    backend=backend,
)
```

In Docker mode, the entry point group is baked into the container image — the host-side configuration doesn't affect it. But the backend still carries the entrypoint so that local fallback and `get-required-fields` work correctly.

### 3. VCS Provider (Optional)

If you want nskit to create repos and push code, configure a VCS provider. Providers are discovered via the `nskit.vcs.providers` entry point and configured via environment variables:

```bash
# GitHub
export GITHUB_TOKEN=ghp_...

# Azure DevOps
export AZURE_DEVOPS_ORG=myorg
export AZURE_DEVOPS_PROJECT=myproject
export AZURE_DEVOPS_PAT=...
```

You can use the VCS provider directly with namespace validation:

```python
from nskit.vcs.repo import Repo, NamespaceValidationRepo
from nskit.vcs.namespace_validator import NamespaceValidator

# Validate the name
validator = NamespaceValidator(options=[...])
ok, msg = validator.validate_name('platform-auth-users')

# Create the repo
repo = Repo(name='platform-auth-users', local_dir=Path('./platform/auth/users'))
repo.create()
```

See [Working with Namespaces](namespaces.md) for namespace configuration.

## Wrapping in a CLI

The simplest platform setup: create a CLI package that pre-configures everything.

```python
# mycompany_cli.py
from nskit.cli.app import create_cli
from nskit.client.backends import GitHubBackend

app = create_cli(
    recipe_entrypoint='mycompany.recipes',
    backend=GitHubBackend(org='myorg'),
)

def main():
    app()
```

```toml
# pyproject.toml
[project.scripts]
myrecipes = "mycompany_cli:main"

[project.dependencies]
nskit = {extras = ["github"]}
```

Users install your package and get a fully configured CLI:

```bash
pip install mycompany-recipes-cli
myrecipes list       # Queries GitHub for available recipes
myrecipes init --recipe python_package   # Interactive prompts, Docker execution
myrecipes update     # 3-way merge from versioned Docker images
```

The CLI is a [Typer](https://typer.tiangolo.com/) app — mount it as a subcommand if you have an existing tool:

```python
parent_app.add_typer(app, name="recipes")
```

## Alternative: Environment Variables

If you don't want a custom CLI package, users can configure nskit via environment variables or a config file:

```bash
export NSKIT_BACKEND_TYPE=github
export NSKIT_BACKEND_ORG=myorg
```

Or pass a config file:

```python
app = create_cli(
    recipe_entrypoint='mycompany.recipes',
    backend='backend-config.yml',
)
```

```yaml
# backend-config.yml
type: github
org: myorg
entrypoint: mycompany.recipes
```

## Web API

The client layer is pure Python — wrap it with any web framework:

```python
from fastapi import FastAPI, HTTPException
from nskit.client import RecipeClient, UpdateClient
from nskit.client.backends import GitHubBackend

app = FastAPI()
backend = GitHubBackend(org='myorg')
recipe_client = RecipeClient(backend)

@app.get("/recipes")
def list_recipes():
    return [r.model_dump() for r in recipe_client.list_recipes()]
```

## Custom Backend

Implement `RecipeBackend` for your infrastructure:

```python
from nskit.client.backends.base import RecipeBackend

class S3Backend(RecipeBackend):
    @property
    def entrypoint(self) -> str:
        return self._entrypoint

    def list_recipes(self): ...
    def get_recipe_versions(self, recipe_name: str): ...
    def fetch_recipe(self, recipe_name: str, version: str, target_path): ...
    def get_image_url(self, recipe: str, version: str) -> str: ...
```

## Error Handling

```python
from nskit.client.exceptions import (
    InitError, UpdateError,
    ProjectNotRecipeBasedError, GitStatusError,
)

try:
    result = update_client.update_project(...)
except GitStatusError as e:
    log.warning(f"Git issue: {e}")
except UpdateError as e:
    log.error(f"Update failed: {e}")
```
