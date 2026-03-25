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

```bash
nskit init --recipe python_package
```

nskit prompts you for each field interactively in your terminal — name, description, owner, etc. Just answer the questions.

If you'd rather provide inputs as a file (useful for CI or scripting):

```bash
nskit init --recipe python_package --input-yaml-path input.yaml
```

### What Happens

nskit runs the recipe from your installed packages and generates the project files. If a backend is configured (see [Platform Integration](platform-integration.md)), it uses the backend's engine instead (typically Docker) for reproducible, versioned execution. See [Docker vs Local Execution](../architecture/docker-execution.md) for the trade-offs.

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
```
