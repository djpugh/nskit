# nskit Recipe System

A flexible, client/service architecture for managing code generation recipes with support for multiple backends and intelligent 3-way merge updates.

## Quick Start by Role

### 🎯 Recipe Users
Generate projects from recipes and keep them updated.

```bash
# List available recipes
myrecipes list

# Initialize a project
myrecipes init --recipe python_package --input-yaml-path config.yaml

# Check for updates
myrecipes check

# Update to latest version
myrecipes update
```

[→ Recipe User Guide](#recipe-users)

### 🔨 Recipe Builders
Create and maintain recipes for your organization.

```python
from nskit.mixer.components import Recipe

class MyRecipe(Recipe):
    """Custom recipe implementation."""
    
    def mix(self):
        # Recipe logic here
        pass
```

[→ Recipe Builder Guide](#recipe-builders)

### ⚙️ Platform Engineers
Deploy and configure recipe systems at scale.

```python
from nskit.cli.app import create_cli
from nskit.client.backends import GitHubBackend

backend = GitHubBackend(org='myorg')
app = create_cli(
    recipe_entrypoint='mycompany.recipes',
    backend=backend
)
```

[→ Platform Engineer Guide](#platform-engineers)

### 👨‍💻 Developers
Extend nskit with custom backends, patterns, and integrations.

```python
from nskit.client.backends.base import RecipeBackend

class CustomBackend(RecipeBackend):
    """Custom backend implementation."""
    
    def list_recipes(self):
        # Custom logic
        pass
```

[→ Developer Reference](developers.md)

---

## Recipe Users

### Prerequisites

Before using recipes, ensure you have the required tools installed:

**For Docker execution (default, production):**
```bash
# Install Docker Desktop
# Visit https://docs.docker.com/get-docker/

# Verify Docker is running
docker info
```

**For GitHub Container Registry:**
```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/

# Authenticate
gh auth login
```

**For local development (--local flag):**
```bash
# Install recipe packages locally
pip install my-recipe
# or for development
pip install -e ./my-recipe
```

### Execution Modes

nskit supports two execution modes:

**Docker Mode (Default)** - Recipes run in containers for consistency:
```bash
myrecipes init --recipe python_package --input-yaml-path config.yaml
```

**Local Mode** - Recipes run from installed packages for development:
```bash
myrecipes init --recipe python_package --input-yaml-path config.yaml --local
```

[→ Docker Execution Guide](docker-execution.md)

**What's the difference?**
- **GitHub Releases**: Recipes distributed as zip archives from GitHub releases (simple, no Docker needed)
- **Docker Registry**: Recipes distributed as Docker images (includes dependencies, guaranteed reproducibility)

**Note:** Your organization will specify which backend they use. Check with your platform team if unsure.

### Installation

```bash
pip install nskit
# or with your organization's CLI
pip install mycompany-recipes-cli
```

### Basic Workflow

**1. Discover Recipes**
```bash
# List all available recipes
myrecipes list

# Search for specific recipes
myrecipes discover --search python
```

**2. Initialize Project**
```bash
# Create input configuration
cat > input.yaml << EOF
project_name: my-project
description: My awesome project
EOF

# Initialize from recipe
myrecipes init \
  --recipe python_package \
  --input-yaml-path input.yaml \
  --output-base-path ./my-project
```

**3. Keep Updated**
```bash
# Check for updates
myrecipes check

# Update to latest (with 3-way merge)
myrecipes update

# Preview changes first
myrecipes update --dry-run

# Update to specific version
myrecipes update --target-version v2.0.0
```

### Understanding Updates

**3-Way Merge**: Preserves your customizations while applying recipe updates
- ✅ Your changes are kept
- ✅ Recipe updates are applied
- ⚠️ Conflicts flagged when both changed same code

**Handling Conflicts**
```bash
# After update with conflicts
git status  # See conflicted files
# Resolve conflicts manually
git add .
git commit -m "Resolved update conflicts"
```

---

## Recipe Builders

### Creating Recipes

**Basic Recipe Structure**
```python
from nskit.mixer.components import Recipe, RecipeConfig
from pathlib import Path

class PythonPackageRecipe(Recipe):
    """Recipe for Python packages."""
    
    def mix(self):
        """Generate project files."""
        # Access input data
        project_name = self.input_data['project_name']
        
        # Render templates
        self.render_template(
            'pyproject.toml.j2',
            output_path=self.output_path / 'pyproject.toml',
            context={'name': project_name}
        )
        
        # Create directories
        (self.output_path / 'src' / project_name).mkdir(parents=True)
```

**Recipe Configuration**
```python
# .recipe/config.yml (auto-generated)
metadata:
  recipe_name: python_package
  recipe_version: v1.0.0
  generated_at: "2026-02-28T14:30:00Z"
```

### Testing Recipes

```python
import pytest
from pathlib import Path
from nskit.mixer.components import Recipe

def test_recipe_generation():
    recipe = Recipe.load('python_package')
    
    input_data = {
        'project_name': 'test-project',
        'description': 'Test'
    }
    
    output = Path('/tmp/test-output')
    recipe.mix(input_data, output)
    
    assert (output / 'pyproject.toml').exists()
```

### Publishing Recipes

**Option 1: GitHub Releases**
```bash
# Tag and release
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0
```

**Option 2: Docker Registry**
```bash
# Build and push
docker build -t ghcr.io/myorg/recipes/python_package:v1.0.0 .
docker push ghcr.io/myorg/recipes/python_package:v1.0.0
```

**Option 3: Local Directory**
```bash
# Just organize in directory structure
recipes/
  python_package/
    v1.0.0/
    v1.1.0/
```

---

## Platform Engineers

### Architecture Overview

```
┌─────────────────────────────────────┐
│     CLI Layer (Thin Wrapper)       │
│  • Commands: init, list, update     │
└─────────────────────────────────────┘
              ▼
┌─────────────────────────────────────┐
│   Client Layer (Pure Python)       │
│  • RecipeClient                     │
│  • UpdateClient                     │
│  • DiscoveryClient                  │
└─────────────────────────────────────┘
              ▼
┌─────────────────────────────────────┐
│   Backend Layer (Pluggable)        │
│  • LocalBackend                     │
│  • DockerBackend                    │
│  • GitHubBackend                    │
└─────────────────────────────────────┘
```

### Deployment Options

**1. CLI Distribution**
```python
# setup.py or pyproject.toml
[project.scripts]
myrecipes = "mycompany.recipes.cli:main"

# cli.py
from nskit.cli.app import create_cli

def main():
    app = create_cli(
        recipe_entrypoint='mycompany.recipes',
        app_name='myrecipes',
        backend='backend-config.yml'
    )
    app()
```

**2. Web API (FastAPI)**
```python
from fastapi import FastAPI
from nskit.client import RecipeClient, UpdateClient
from nskit.client.backends import GitHubBackend

app = FastAPI()
backend = GitHubBackend(org='myorg')
recipe_client = RecipeClient(backend)
update_client = UpdateClient(backend)

@app.get("/recipes")
def list_recipes():
    return recipe_client.list_recipes()

@app.post("/projects/{project_id}/update")
def update_project(project_id: str):
    result = update_client.update_project(
        project_path=Path(f'/projects/{project_id}'),
        target_version='latest'
    )
    return result.dict()
```

**3. Programmatic Usage**
```python
from nskit.client import RecipeClient
from nskit.client.backends import DockerBackend

# Configure backend
backend = DockerBackend(
    registry_url='ghcr.io',
    image_prefix='myorg/recipes',
    auth_token=os.getenv('GITHUB_TOKEN')
)

# Use client
client = RecipeClient(backend)
recipes = client.list_recipes()

# Initialize recipe
result = client.initialize_recipe(
    recipe='python_package',
    version='v1.0.0',
    parameters={'project_name': 'my-project'},
    output_dir=Path('./output')
)
```

### Backend Configuration

**Local Backend**
```yaml
# backend-config.yml
type: local
path: /path/to/recipes
entrypoint: mycompany.recipes
```

**Docker Backend**
```yaml
type: docker
registry_url: ghcr.io
image_prefix: myorg/recipes
auth_token: ${GITHUB_TOKEN}
entrypoint: mycompany.recipes
```

**GitHub Backend**
```yaml
type: github
org: myorg
repo_pattern: recipe-{recipe_name}
token: ${GITHUB_TOKEN}
entrypoint: mycompany.recipes
```

### Multi-Backend Setup

```python
from nskit.client.backends import create_backend_from_config

# Production: GitHub releases
prod_backend = create_backend_from_config({
    'type': 'github',
    'org': 'myorg',
    'repo_pattern': 'recipe-{recipe_name}'
})

# Development: Local filesystem
dev_backend = create_backend_from_config({
    'type': 'local',
    'path': '/path/to/dev/recipes'
})

# Use based on environment
backend = prod_backend if ENV == 'prod' else dev_backend
```

### Monitoring & Observability

```python
import logging
from nskit.client import UpdateClient

# Configure logging
logging.basicConfig(level=logging.INFO)

# Track update operations
client = UpdateClient(backend)
result = client.update_project(
    project_path=Path('/projects/my-project'),
    target_version='v2.0.0'
)

# Log metrics
if result.success:
    logger.info(f"Updated {len(result.files_updated)} files")
    if result.files_with_conflicts:
        logger.warning(f"Conflicts: {result.files_with_conflicts}")
else:
    logger.error(f"Update failed: {result.errors}")
```

### Security Considerations

**Token Management**
```python
# Use environment variables
import os
backend = GitHubBackend(
    org='myorg',
    token=os.getenv('GITHUB_TOKEN')  # Never hardcode
)

# Or use secret management
from your_secrets import get_secret
backend = GitHubBackend(
    org='myorg',
    token=get_secret('github-token')
)
```

**Access Control**
- Use private registries for proprietary recipes
- Implement authentication in web API layer
- Restrict backend access via IAM/RBAC

---

## Advanced Topics

### Custom Backends

```python
from nskit.client.backends.base import RecipeBackend
from nskit.recipes.models import RecipeInfo

class S3Backend(RecipeBackend):
    """Backend for S3-stored recipes."""
    
    @property
    def entrypoint(self) -> str:
        return self._entrypoint
    
    def list_recipes(self) -> List[RecipeInfo]:
        # Implement S3 listing
        pass
    
    def get_recipe_versions(self, recipe_name: str) -> List[str]:
        # Implement version listing
        pass
    
    def fetch_recipe(self, recipe_name: str, version: str, target_path: Path) -> Path:
        # Implement S3 download
        pass
```

### Migration from Legacy Systems

```python
# Wrap existing recipe system
from nskit.cli.app import create_cli
from legacy_recipes import LegacyRecipeSystem

class LegacyBackend(RecipeBackend):
    def __init__(self):
        self.legacy = LegacyRecipeSystem()
    
    def list_recipes(self):
        return [
            RecipeInfo(name=r.name, versions=[r.version])
            for r in self.legacy.get_all_recipes()
        ]

# Gradual migration
app = create_cli(
    recipe_entrypoint='company.recipes',
    backend=LegacyBackend()
)
```

---

## Troubleshooting

### Common Issues

**Update Conflicts**
```bash
# Problem: Merge conflicts after update
# Solution: Resolve manually
git status
# Edit conflicted files
git add .
git commit -m "Resolved conflicts"
```

**Backend Authentication**
```bash
# Problem: Docker pull fails
# Solution: Authenticate
docker login ghcr.io -u token --password-stdin < token.txt

# Problem: GitHub API rate limit
# Solution: Use authenticated token
export GITHUB_TOKEN=your_token
```

**Recipe Not Found**
```bash
# Problem: Recipe not discovered
# Solution: Check backend configuration
myrecipes list  # Verify recipe appears
# Check backend config path/org/registry
```

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all operations show detailed logs
client.update_project(...)
```

---

## API Reference

See [API Documentation](api.md) for complete reference.

## Contributing

See [Contributing Guide](contributing.md) for development setup.

## License

MIT License - see [LICENSE](LICENSE) for details.
