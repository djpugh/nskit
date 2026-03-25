# nskit Recipe System

Flexible, client/service architecture for managing code generation recipes with intelligent 3-way merge updates.

## Architecture

nskit is organized into focused modules:

- **`client/`** - Recipe operations (initialization, updates, backends, diff/merge)
- **`mixer/`** - Core templating and component system
- **`recipes/`** - Pre-defined recipe implementations
- **`cli/`** - Command-line interface (thin wrapper over client)

## Quick Start

### For Recipe Users

```bash
# Install
pip install nskit

# List recipes
myrecipes list

# Initialize project (Docker mode - default)
myrecipes init --recipe python_package --input-yaml-path config.yaml

# Initialize project (local mode - development)
myrecipes init --recipe python_package --input-yaml-path config.yaml --local

# Update project
myrecipes update
```

### For Recipe Builders

```python
from nskit.mixer.components import Recipe

class MyRecipe(Recipe):
    def mix(self):
        self.render_template('template.j2', output_path=self.output_path / 'file.py')
```

### For Platform Engineers

```python
from nskit.cli.app import create_cli
from nskit.client.backends import GitHubBackend

app = create_cli(
    recipe_entrypoint='mycompany.recipes',
    backend=GitHubBackend(org='myorg')
)
```

## Features

- **Two Execution Modes** — Docker (production, recommended) or local (recipe development)
- **Reproducible Updates** — Docker mode pins each recipe version as an immutable image, enabling deterministic 3-way merges
- **Client/Service Architecture** — Use programmatically, via CLI, or wrap with web API
- **Multiple Backends** — Local filesystem, Docker registry, GitHub releases
- **3-Way Merge Updates** — Preserves user customisations while applying recipe updates
- **Conflict Detection** — Intelligent merge with conflict reporting
- **Pluggable** — Easy to extend with custom backends

## Architecture

```
CLI Layer (Thin Wrapper)
    ↓
Client Layer (Pure Python)
    ↓
Engine Layer (Docker or Local)
    ↓
Backend Layer (Pluggable)
```

## Documentation

Full documentation: [https://docs.example.com](https://docs.example.com)

- [Using a Recipe](docs/source/guides/using-a-recipe.md)
- [Updating from a Recipe](docs/source/guides/updating-from-a-recipe.md)
- [Building a Recipe](docs/source/guides/building-a-recipe.md)
- [Platform Integration](docs/source/guides/platform-integration.md)

## Installation

```bash
# Basic installation
pip install nskit

# With GitHub support
pip install nskit[github]

# With Docker support
pip install nskit[docker]

# With all extras
pip install nskit[all]
```

## Backend Options

nskit supports multiple backends for recipe distribution:

| Backend | Discovery | Execution | Use Case | Setup |
|---------|-----------|-----------|----------|-------|
| **LocalBackend** | Local files | Local only | Development | None |
| **GitHubBackend** | GitHub Releases | Docker (ghcr.io) | Production | gh CLI + Docker |
| **DockerBackend** | Docker registry | Docker | Custom registries | Docker |

**Execution Modes:**
- **Docker Mode (Default)** — Recipes run in versioned containers. Each version is a pinned image, enabling deterministic 3-way merge updates. Recommended for production.
- **Local Mode (`--local`)** — Recipes run from locally installed Python packages. Faster, but the output may vary across environments. Best for recipe development only.

See [Architecture](docs/source/architecture/index.md) for the detailed design rationale and [Docker vs Local Execution](docs/source/architecture/docker-execution.md) for the execution flow.

## Usage Examples

### Programmatic Usage

```python
from nskit.client import RecipeClient, UpdateClient
from nskit.client.engines import LocalEngine, DockerEngine
from nskit.client.backends import GitHubBackend
from pathlib import Path

# Initialise backend
backend = GitHubBackend(org='myorg')

# Create client with Docker engine (default, recommended)
client = RecipeClient(backend)

# Or with local engine for recipe development
client = RecipeClient(backend, engine=LocalEngine())

# List recipes
recipes = client.list_recipes()

# Initialize recipe
result = client.initialize_recipe(
    recipe='python_package',
    version='v1.0.0',
    parameters={'name': 'my-project'},
    output_dir=Path('./output')
)

# Update project
update_client = UpdateClient(backend)
result = update_client.update_project(
    project_path=Path('./my-project'),
    target_version='v2.0.0'
)
```

### CLI Usage

```bash
# Discover recipes
myrecipes discover --search python

# Initialize project
myrecipes init \
  --recipe python_package \
  --input-yaml-path input.yaml \
  --output-base-path ./output

# Check for updates
myrecipes check

# Update with dry-run
myrecipes update --dry-run

# Update to specific version
myrecipes update --target-version v2.0.0
```

### Web API Usage

```python
from fastapi import FastAPI
from nskit.client import RecipeClient
from nskit.client.backends import GitHubBackend

app = FastAPI()
backend = GitHubBackend(org='myorg')
client = RecipeClient(backend)

@app.get("/recipes")
def list_recipes():
    return client.list_recipes()
```

## Backend Configuration

### Local Backend
```yaml
type: local
path: /path/to/recipes
```

### Docker Backend
```yaml
type: docker
registry_url: ghcr.io
image_prefix: myorg/recipes
auth_token: ${GITHUB_TOKEN}
```

### GitHub Backend
```yaml
type: github
org: myorg
repo_pattern: recipe-{recipe_name}
token: ${GITHUB_TOKEN}
```

## Development

```bash
# Clone repository
git clone https://github.com/yourorg/nskit.git
cd nskit

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Build docs
mkdocs serve
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: [https://docs.example.com](https://docs.example.com)
- Issues: [GitHub Issues](https://github.com/yourorg/nskit/issues)
- Discussions: [GitHub Discussions](https://github.com/yourorg/nskit/discussions)
