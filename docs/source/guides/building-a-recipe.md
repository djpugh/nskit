# Building a Recipe

Recipes are just Python classes with some files. They work for any language — Python, Terraform, TypeScript, whatever. nskit doesn't care what's inside the templates.

## Getting Started

The fastest way to create a new recipe is to use nskit's built-in `recipe` recipe:

```bash
nskit init --recipe recipe
```

This generates a complete recipe project with:

- Recipe class and ingredient template
- Dockerfile with `nskit.recipe` labels pre-configured
- pyproject.toml with entry point registration
- Tests, docs, git, and pre-commit setup

Then customise the generated recipe class and templates to your needs.

## The Basics

```python
from nskit.mixer.components import Recipe, File

class HelloRecipe(Recipe):
    name: str = "hello"
    contents = [
        File(id_="readme", name="README.md", content="# {{name}}\n"),
    ]
```

That's a working recipe. It generates one file.

## Template Files

Place `.jinja` files alongside your recipe module and reference them with `package:filename`:

```python
class MyRecipe(Recipe):
    name: str = "my-project"
    contents = [
        File(id_="pyproject", name="pyproject.toml",
             content="my_recipe:pyproject.toml.jinja"),
        File(id_="readme", name="README.md",
             content="my_recipe:readme.md.jinja"),
        Folder(id_="src", name="src", contents=[
            File(id_="init", name="__init__.py",
                 content="my_recipe:__init__.py.jinja"),
        ]),
    ]
```

## Non-Python Examples

Terraform module:

```python
class TerraformModuleRecipe(Recipe):
    name: str = RecipeField(default="my-module", prompt_text="Module name")
    cloud_provider: str = RecipeField(default="aws", prompt_text="Cloud provider")

    contents = [
        File(id_="main", name="main.tf",
             content="my_recipes.terraform:main.tf.jinja"),
        File(id_="variables", name="variables.tf",
             content="my_recipes.terraform:variables.tf.jinja"),
        File(id_="readme", name="README.md",
             content="# {{name}}\n\nTerraform module for {{cloud_provider}}.\n"),
    ]
```

TypeScript app:

```python
class TypeScriptAppRecipe(Recipe):
    name: str = RecipeField(default="my-app", prompt_text="App name")

    contents = [
        File(id_="pkg", name="package.json",
             content="my_recipes.typescript:package.json.jinja"),
        Folder(id_="src", name="src", contents=[
            File(id_="index", name="index.ts",
                 content="my_recipes.typescript:index.ts.jinja"),
        ]),
    ]
```

## Input Fields

```python
from nskit.mixer.components.recipe import Recipe, RecipeField

class MyRecipe(Recipe):
    name: str = RecipeField(default="my-pkg", prompt_text="Package name")
    use_docker: bool = RecipeField(default=False, prompt_text="Include Docker?")
```

Users get prompted interactively via the CLI.

## Hooks

```python
from nskit.mixer.hooks.git import GitInit
from nskit.mixer.hooks.pre_commit import PrecommitInstall

class MyRecipe(Recipe):
    post_hooks = [GitInit(), PrecommitInstall()]
    contents = [...]
```

## Sharing Ingredients

Don't copy-paste — share ingredients across recipes:

```python
from my_company.ingredients import ci_pipeline, linting_config

class PackageRecipe(Recipe):
    contents = [ci_pipeline, linting_config, src_dir, ...]

class APIRecipe(Recipe):
    contents = [ci_pipeline, linting_config, docker_setup, api_src_dir, ...]
```

Update `ci_pipeline` once, both recipes get it. See [Recipe Architecture](../architecture/recipes.md) for the full composition model.

## Entry Points

Register your recipe so nskit can discover it:

```toml
[project.entry-points."mycompany.recipes"]
my_recipe = "my_package.recipes:MyRecipe"
terraform_module = "my_package.recipes:TerraformModuleRecipe"
```

The group name must match the `entrypoint` parameter used by the CLI.

## Testing

```python
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from nskit.client.engines import LocalEngine

class TestMyRecipe(unittest.TestCase):
    def test_creates_project(self):
        engine = LocalEngine()
        with TemporaryDirectory() as tmp:
            result = engine.execute(
                recipe="my_recipe", version="local",
                parameters={"name": "test"},
                output_dir=Path(tmp) / "out",
                entrypoint="my_package.recipes",
            )
            self.assertTrue(result.success, result.errors)
```

## Distribution

### Local (Python Package)

Ship as a Python package. Users install it and nskit discovers it via entry points:

```bash
pip install my-recipes
nskit list    # Shows your recipes
nskit init --recipe my_recipe
```

This is the simplest option but doesn't support reproducible updates. See [Docker vs Local Execution](../architecture/docker-execution.md).

### Docker (Recommended for Production)

Ship as a Docker image. The image contains nskit + your recipe package. The `recipe` recipe (`nskit init --recipe recipe`) generates a Dockerfile with the correct labels for discovery.

```bash
# Build with nskit labels (RECIPE_NAME sets nskit.recipe.name label)
docker build --build-arg RECIPE_NAME=python_package \
    -t ghcr.io/myorg/python_package:v1.0.0 .

# Use locally without a registry
nskit --backend docker-local list
nskit --backend docker-local init --recipe python_package

# Or push to a registry for team use
docker push ghcr.io/myorg/python_package:v1.0.0
```

Images must have these labels:

| Label | Required | Purpose |
|-------|----------|---------|
| `nskit.recipe=true` | Yes | Marks image as an nskit recipe |
| `nskit.recipe.name=<name>` | Yes | Canonical recipe name |

The image tag is used as the version. The `recipe` recipe generates a Dockerfile with these labels:

```dockerfile
# Generated by nskit init --recipe recipe
ARG RECIPE_NAME=nskit
# ...
LABEL nskit.recipe="true"
LABEL nskit.recipe.name="${RECIPE_NAME}"
ENTRYPOINT ["sh", "-c", "uv run --no-sync $CLI_COMMAND \"$@\"", "--"]
```

Build with:

```bash
docker build --target runtime \
    --build-arg RECIPE_NAME=python_package \
    -t myorg/python_package:v1.0.0 .
```

**Option A: Use the `recipe` recipe** (recommended) — generates a Dockerfile with the correct labels:

```bash
nskit init --recipe recipe
# The generated project includes a Dockerfile with nskit.recipe labels
docker build --build-arg RECIPE_NAME=my_recipe -t myorg/my_recipe:v1.0.0 .
```

**Option B: Write your own Dockerfile** — just include the two labels:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install .
LABEL nskit.recipe="true"
LABEL nskit.recipe.name="my_recipe"
ENTRYPOINT ["nskit"]
```

**One recipe per image.** Each recipe gets its own image, independently versioned. This keeps images small and lets teams release at their own pace. Docker registries deduplicate shared layers, so common base layers (Python, nskit, shared dependencies) are stored once regardless of how many recipe images you have.

The `nskit.recipe.name` label is the canonical recipe name. Backends use their naming conventions (repo patterns, image prefixes) to narrow where to look, but the label on the image is the source of truth. At list time, backends read the label from the registry manifest (no pull needed). At init time, nskit reads it from the pulled image to pass the correct name to the container.

**Backend options for Docker images:**

- `--backend docker-local` — discovers from locally pulled images (no registry needed)
- `GitHubBackend` — discovers from GitHub releases, pulls from ghcr.io
- `DockerBackend` — discovers from any Docker registry

See [Platform Integration](platform-integration.md) for backend configuration.

### GitHub Releases

The `GitHubBackend` discovers versions from release tags and resolves Docker images from ghcr.io. So publishing is:

```bash
git tag v1.0.0 && git push origin v1.0.0
gh release create v1.0.0
# Also build and push the Docker image for this tag
docker build -t ghcr.io/myorg/my-recipe:v1.0.0 .
docker push ghcr.io/myorg/my-recipe:v1.0.0
```

## Versioning

- Semantic versioning: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Test updates from previous versions before releasing
- Document breaking changes
