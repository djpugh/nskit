# Using a Recipe

You've been told there's a recipe for your project type. Here's how to go from zero to a working project.

## Prerequisites

- `pip install nskit`
- The recipe package installed (`pip install my-recipes`), or a backend configured by your platform team

## 1. See What's Available

```bash
nskit list
```

This discovers recipes from installed packages. If your platform team has configured a backend, it also shows remotely published recipes and their versions (the backend overrides the default list with what's available in the registry).

## 2. Initialise Your Project

![YAML Init Demo](../assets/demo-yaml.gif)

```bash
nskit init --recipe python_package
```

nskit prompts you for each field interactively. Defaults are pre-filled from (in priority order):

1. **Recipe-defined env var** — `RecipeField(env_var="CUSTOM_VAR")` if the recipe author specified one
2. **Convention env var** — `RECIPE_` + field name, e.g. `RECIPE_NAME`, `RECIPE_REPO_OWNER`, `RECIPE_REPO_EMAIL`
3. **Template expression** — `RecipeField(template="{{name | lower}}")` evaluated against already-entered values
4. **Git config** — `user.name` for owner, `user.email` for email

Press Enter to accept a default, or type to override it.

If you'd rather provide inputs as a file (useful for CI or scripting):

```bash
nskit init --recipe python_package --input-yaml-path input.yaml
```

### What Happens

nskit runs the recipe from your installed packages and generates the project files. If a backend is configured (see [Platform Integration](platform-integration.md)), it uses the backend's engine instead (typically Docker) for reproducible, versioned execution. See [Docker vs Local Execution](../architecture/docker-execution.md) for the trade-offs.

If a VCS provider is configured (e.g. `GITHUB_TOKEN` is set), nskit prompts during field collection:

```
Create repository in GitHub? [Y/n]
```

After generating the project, nskit always commits the initial files. If you accepted the repo prompt, it also creates the remote repository and pushes. Declining skips the remote — you can always create it manually later.

### Docker mode with local images

If you have Docker recipe images locally, you can use them directly:

![Docker Mode Demo](../assets/demo-docker.gif)

```bash
nskit --backend docker-local list
nskit --backend docker-local init --recipe python_package
```

## 3. Stay Updated

```bash
nskit check                              # Anything new?
nskit update --dry-run                   # What would change?
nskit update                             # Apply it (3-way merge)
nskit update --target-version v2.0.0     # Or pick a specific version
```

Your customisations are preserved. The recipe's changes are applied. Conflicts are flagged. See [Updating from a Recipe](updating-from-a-recipe.md) for the details.

!!! note "Updates require a backend"
    `nskit check` and `nskit update` need a configured backend to discover new versions and pull the correct recipe images. See [Platform Integration](platform-integration.md) for how to set one up. Without a backend, update the recipe package manually and re-initialise.

## Programmatic Usage

```python
from nskit.client import RecipeClient
from nskit.client.engines import LocalEngine
from pathlib import Path

client = RecipeClient(backend, engine=LocalEngine())

result = client.initialize_recipe(
    recipe='python_package',
    version='v1.0.0',
    parameters={'name': 'my-project', 'repo': {...}},
    output_dir=Path('./my-project'),
)

# Optionally create a remote repository (auto-detects VCS provider)
if result.success:
    ok, msg = client.create_repository('my-project', description='My new project')
```
