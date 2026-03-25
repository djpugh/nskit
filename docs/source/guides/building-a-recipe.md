# Building a Recipe

Recipes are just Python classes with some files. They work for any language — Python, Terraform, TypeScript, whatever. nskit doesn't care what's inside the templates.

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

Ship as a Docker image. The image contains nskit + your recipe package. A backend maps recipe names to image URLs — for example, the `GitHubBackend` maps `python_package` version `v1.0.0` to `ghcr.io/myorg/python_package:v1.0.0`.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install .
ENTRYPOINT ["python", "-m", "nskit.cli"]
```

```bash
# Build and push to GitHub Container Registry
# (matches what GitHubBackend expects: ghcr.io/<org>/<recipe_name>:<version>)
docker build -t ghcr.io/myorg/python_package:v1.0.0 .
docker push ghcr.io/myorg/python_package:v1.0.0
```

For users to pull these images, your platform team needs to configure a backend that points to the registry. See [Platform Integration](platform-integration.md) for the full setup.

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
