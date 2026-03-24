# Developer Guide

Complete API reference and patterns for extending nskit.

---

## API Reference

### Client APIs

#### RecipeClient

```python
from nskit.client import RecipeClient
from nskit.client.backends import LocalBackend

backend = LocalBackend(recipes_dir=Path('/recipes'))
client = RecipeClient(backend)
```

**Methods:**

```python
def list_recipes() -> List[RecipeInfo]:
    """List all available recipes from backend."""

def get_recipe_versions(recipe: str) -> List[str]:
    """Get available versions for a recipe."""

def initialize_recipe(
    recipe: str,
    version: str,
    parameters: Dict[str, Any],
    output_dir: Path,
    force: bool = False,
) -> RecipeResult:
    """Initialize a recipe with given parameters."""
```

#### UpdateClient

```python
from nskit.client import UpdateClient

client = UpdateClient(backend)
```

**Methods:**

```python
def check_update_available(project_path: Path) -> Optional[str]:
    """Check if update is available. Returns latest version or None."""

def update_project(
    project_path: Path,
    target_version: str,
    diff_mode: DiffMode = DiffMode.THREE_WAY,
    dry_run: bool = False,
) -> UpdateResult:
    """Update project to target version with 3-way merge."""
```

#### DiscoveryClient

```python
from nskit.client import DiscoveryClient

client = DiscoveryClient(backend)
```

**Methods:**

```python
def discover_recipes(search_term: Optional[str] = None) -> List[RecipeInfo]:
    """Discover recipes with optional search filter."""

def get_recipe_info(recipe_name: str) -> Optional[RecipeInfo]:
    """Get detailed info for specific recipe."""

def get_recipe_versions(recipe_name: str) -> List[str]:
    """Get available versions for a recipe."""
```

#### RepositoryClient

```python
from nskit.recipes import RepositoryClient

client = RepositoryClient(vcs_client)
```

**Methods:**

```python
def create_repository(
    repo_name: str,
    description: Optional[str] = None,
    private: bool = True,
) -> RepositoryInfo:
    """Create a new repository."""

def configure_repository(
    repo_name: str,
    branch_protection: bool = True,
    require_reviews: bool = True,
) -> None:
    """Configure repository settings."""

def get_repository_info(repo_name: str) -> Optional[RepositoryInfo]:
    """Get repository information."""
```

---

### Backend APIs

#### RecipeBackend (Abstract)

```python
from nskit.client.backends.base import RecipeBackend
from abc import ABC, abstractmethod

class RecipeBackend(ABC):
    @property
    @abstractmethod
    def entrypoint(self) -> str:
        """Recipe entrypoint name."""
    
    @abstractmethod
    def list_recipes(self) -> List[RecipeInfo]:
        """List available recipes."""
    
    @abstractmethod
    def get_recipe_versions(self, recipe_name: str) -> List[str]:
        """Get versions for a recipe."""
    
    @abstractmethod
    def fetch_recipe(
        self, recipe_name: str, version: str, target_path: Path
    ) -> Path:
        """Fetch recipe to target path."""
```

#### LocalBackend

```python
from nskit.client.backends import LocalBackend

backend = LocalBackend(
    recipes_dir=Path('/path/to/recipes'),
    entrypoint='mycompany.recipes'
)
```

**Use case:** Development and testing with local recipe files.

#### GitHubBackend

```python
from nskit.client.backends import GitHubBackend

backend = GitHubBackend(
    org='myorg',
    repo_pattern='recipe-{recipe_name}',
    token=os.getenv('GITHUB_TOKEN')
)
```

**Use case:** Simple distribution via GitHub releases (zip files).

#### DockerBackend

```python
from nskit.client.backends import DockerBackend

backend = DockerBackend(
    registry_url='ghcr.io',
    image_prefix='myorg/recipes',
    auth_token=os.getenv('GITHUB_TOKEN')
)
```

**Use case:** Production distribution with versioning and dependency isolation.

**Prerequisites:** Docker must be installed and running.

---

### Backend Selection Guide

#### How Each Backend Works

**Important:** Currently, all backends load recipes from **installed Python packages** via entrypoints. The backend's `fetch_recipe()` method is not used in the current implementation.

**LocalBackend**
- Lists recipes from a local directory
- Recipes must be installed as Python packages
- Used for development and testing

**GitHubBackend**
- Lists recipes and versions from GitHub Releases
- **Does NOT download recipe code** - only used for discovery
- Recipes must be installed as Python packages via `pip install`
- Versions are release tags (e.g., v1.0.0, v2.0.0)

**DockerBackend**
- Lists recipes from Docker registry tags
- **Does NOT pull images** - only used for discovery
- Recipes must be installed as Python packages
- Could be enhanced to pull images and use recipes from them

**Current Architecture:**
```python
# Backend is only used for listing
recipes = backend.list_recipes()
versions = backend.get_recipe_versions("python_package")

# Recipe loading uses installed packages, NOT backend
recipe = Recipe.load("python_package", entrypoint="mycompany.recipes")
```

**Future Enhancement:**
The `fetch_recipe()` method exists but is unused. Future versions could:
1. Download recipe from backend
2. Install it temporarily or use it directly
3. Remove dependency on pre-installed packages

#### Workflow Comparison

**Current Reality: All backends require pre-installed packages**

**GitHub Releases Workflow:**
```bash
# 1. Developer publishes recipe package to PyPI
pip install build
python -m build
twine upload dist/*

# 2. Developer creates GitHub release (for version tracking)
git tag v1.0.0
git push origin v1.0.0
gh release create v1.0.0

# 3. User installs package and uses CLI
pip install mycompany-recipes==1.0.0  # Install recipe package
myrecipes list  # Backend lists versions from GitHub releases
myrecipes init --recipe python_package  # Uses installed package, NOT downloaded
```

**Docker Registry Workflow:**
```bash
# 1. Developer publishes recipe package to PyPI
twine upload dist/*

# 2. Developer tags Docker image (for version tracking)
docker tag myimage:latest ghcr.io/org/recipes:v1.0.0
docker push ghcr.io/org/recipes:v1.0.0

# 3. User installs package and uses CLI
pip install mycompany-recipes==1.0.0  # Install recipe package
myrecipes list  # Backend lists versions from Docker tags
myrecipes init --recipe python_package  # Uses installed package, NOT pulled image
```

**Key Insight:**
Backends are currently **only used for version discovery**, not for fetching recipe code. All recipes must be pre-installed as Python packages.

#### Why Docker for Recipe Distribution?

Docker provides several advantages for managing recipe versions and configuration:

**1. Immutable Versioning** - Each recipe version is a tagged image that never changes  
**2. Easy Distribution** - Free hosting on registries with built-in auth and CDN  
**3. Dependency Isolation** - Recipe dependencies bundled, no "works on my machine" issues  
**4. Efficient Storage** - Layer caching reduces bandwidth and disk usage  
**5. Standard Tooling** - Widely adopted with excellent CLI tools  
**6. CI/CD Integration** - Easy to build and publish in pipelines

#### When to Use Each Backend

**Important:** All backends currently require recipes to be installed as Python packages. Backends are only used for **listing recipes and versions**.

| Backend | Version Source | Best For |
|---------|----------------|----------|
| **LocalBackend** | Local directory | Development, testing |
| **GitHubBackend** | GitHub Releases | Public recipes, version tracking via releases |
| **DockerBackend** | Docker image tags | Version tracking via container tags |

**Choose GitHub Releases when:**
- You want to track recipe versions using GitHub releases
- You want release notes and changelogs
- Your recipes are open source
- You're already using GitHub

**Choose Docker when:**
- You want to track versions using Docker image tags
- You're already using Docker for other tools
- You have a private container registry

**Choose Local when:**
- You're developing and testing recipes
- You don't need version tracking

**All require:** `pip install mycompany-recipes` to install the actual recipe code.

---

### Backend APIs

#### RecipeBackend (Abstract)

```python
from nskit.client.backends.base import RecipeBackend

class CustomBackend(RecipeBackend):
    @property
    def entrypoint(self) -> str:
        return "mycompany.recipes"
    
    def list_recipes(self) -> List[RecipeInfo]:
        # Implementation
        pass
```

#### LocalBackend

```python
from nskit.client.backends import LocalBackend

backend = LocalBackend(
    recipes_dir=Path('/path/to/recipes'),
    entrypoint='mycompany.recipes'
)
```

#### GitHubBackend

```python
from nskit.client.backends import GitHubBackend

backend = GitHubBackend(
    org='myorg',
    repo_pattern='recipe-{recipe_name}',
    token=os.getenv('GITHUB_TOKEN'),
    entrypoint='mycompany.recipes'
)
```

---

### Utility APIs

#### GitUtils

```python
from nskit.mixer.utils import GitUtils

git = GitUtils(project_path=Path('./project'))
```

**Methods:**

```python
def is_git_repository() -> bool:
    """Check if path is a git repository."""

def has_uncommitted_changes() -> bool:
    """Check for uncommitted changes."""

def get_current_commit() -> Optional[str]:
    """Get current commit hash."""

def merge_file(
    base_content: str,
    user_content: str,
    template_content: str,
) -> Tuple[str, bool]:
    """Perform 3-way merge using git merge-file. Returns (merged_content, has_conflicts)."""

def diff_files(old_path: Path, new_path: Path) -> str:
    """Get diff between two files."""
```

#### DiffEngine

```python
from nskit.mixer.update import DiffEngine, DiffMode

engine = DiffEngine(context_lines=3)
```

**Methods:**

```python
def extract_diff(
    old_path: Path,
    new_path: Path,
    diff_mode: DiffMode = DiffMode.TWO_WAY
) -> DiffResult:
    """Extract differences between two paths."""
```

---

### Model APIs

#### RecipeInfo

```python
from nskit.recipes.models import RecipeInfo

recipe = RecipeInfo(
    name='python_package',
    versions=['v1.0.0', 'v1.1.0'],
    description='Python package recipe'
)
```

#### UpdateResult

```python
from nskit.recipes.models import UpdateResult

result = UpdateResult(
    success=True,
    files_updated=['file1.py', 'file2.py'],
    files_with_conflicts=['file3.py'],
    clean_merges=['file1.py', 'file2.py'],
    errors=[],
    warnings=[]
)
```

#### DiffResult

```python
from nskit.mixer.update import DiffResult, FileDiff, DiffType

result = DiffResult(
    added_files=[FileDiff(path=..., relative_path='new.py', diff_type=DiffType.ADDED)],
    deleted_files=[],
    modified_files=[FileDiff(path=..., relative_path='old.py', diff_type=DiffType.MODIFIED)]
)
```

---

## Design Patterns

### Pattern 1: Custom Backend

Implement custom backend for your storage system:

```python
from nskit.client.backends.base import RecipeBackend
from nskit.recipes.models import RecipeInfo
import boto3

class S3Backend(RecipeBackend):
    """Backend for S3-stored recipes."""
    
    def __init__(self, bucket: str, prefix: str = '', entrypoint: str = 'nskit.recipes'):
        self.s3 = boto3.client('s3')
        self.bucket = bucket
        self.prefix = prefix
        self._entrypoint = entrypoint
    
    @property
    def entrypoint(self) -> str:
        return self._entrypoint
    
    def list_recipes(self) -> List[RecipeInfo]:
        """List recipes from S3."""
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=self.prefix,
            Delimiter='/'
        )
        
        recipes = []
        for prefix in response.get('CommonPrefixes', []):
            recipe_name = prefix['Prefix'].rstrip('/').split('/')[-1]
            versions = self.get_recipe_versions(recipe_name)
            recipes.append(RecipeInfo(name=recipe_name, versions=versions))
        
        return recipes
    
    def get_recipe_versions(self, recipe_name: str) -> List[str]:
        """Get versions from S3."""
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f'{self.prefix}/{recipe_name}/',
            Delimiter='/'
        )
        
        versions = []
        for prefix in response.get('CommonPrefixes', []):
            version = prefix['Prefix'].rstrip('/').split('/')[-1]
            versions.append(version)
        
        return sorted(versions, reverse=True)
    
    def fetch_recipe(
        self, recipe_name: str, version: str, target_path: Path
    ) -> Path:
        """Download recipe from S3."""
        prefix = f'{self.prefix}/{recipe_name}/{version}/'
        
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix
        )
        
        for obj in response.get('Contents', []):
            key = obj['Key']
            relative_path = key[len(prefix):]
            local_path = target_path / relative_path
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.s3.download_file(self.bucket, key, str(local_path))
        
        return target_path

# Usage
backend = S3Backend(bucket='my-recipes', prefix='recipes')
client = RecipeClient(backend)
```

### Pattern 2: Backend Factory

Create backends from configuration:

```python
from nskit.client.backends import create_backend_from_config
import os

def get_backend():
    """Get backend based on environment."""
    env = os.getenv('ENV', 'dev')
    
    configs = {
        'dev': {
            'type': 'local',
            'path': './recipes'
        },
        'staging': {
            'type': 'github',
            'org': 'myorg',
            'repo_pattern': 'recipe-{recipe_name}-staging'
        },
        'prod': {
            'type': 'github',
            'org': 'myorg',
            'repo_pattern': 'recipe-{recipe_name}'
        }
    }
    
    return create_backend_from_config(configs[env])

# Usage
backend = get_backend()
client = RecipeClient(backend)
```

### Pattern 3: Multi-Backend Aggregation

Aggregate recipes from multiple backends:

```python
from nskit.client import RecipeClient
from nskit.client.backends import LocalBackend, GitHubBackend

class MultiBackendClient:
    """Client that aggregates multiple backends."""
    
    def __init__(self, backends: List[RecipeBackend]):
        self.clients = [RecipeClient(b) for b in backends]
    
    def list_recipes(self) -> List[RecipeInfo]:
        """List recipes from all backends."""
        all_recipes = {}
        
        for client in self.clients:
            for recipe in client.list_recipes():
                if recipe.name in all_recipes:
                    # Merge versions
                    all_recipes[recipe.name].versions.extend(recipe.versions)
                else:
                    all_recipes[recipe.name] = recipe
        
        return list(all_recipes.values())

# Usage
backends = [
    LocalBackend(recipes_dir=Path('./local-recipes')),
    GitHubBackend(org='myorg')
]
client = MultiBackendClient(backends)
```

### Pattern 4: Custom Recipe Base Class

Extend Recipe with common functionality:

```python
from nskit.mixer.components import Recipe
from pathlib import Path

class CompanyRecipe(Recipe):
    """Base recipe with company-specific features."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_templates = Path(__file__).parent / 'templates'
    
    def render_company_template(self, template_name: str, **context):
        """Render template from company template directory."""
        template_path = self.company_templates / template_name
        output_path = self.output_path / template_name.replace('.j2', '')
        
        self.render_template(
            str(template_path),
            output_path=output_path,
            context=context
        )
    
    def add_company_metadata(self):
        """Add standard company metadata."""
        metadata = {
            'company': 'MyCompany',
            'generated_by': 'nskit',
            'support': 'support@mycompany.com'
        }
        
        metadata_file = self.output_path / '.company-metadata.json'
        metadata_file.write_text(json.dumps(metadata, indent=2))

# Usage
class PythonPackageRecipe(CompanyRecipe):
    def mix(self):
        self.render_company_template('pyproject.toml.j2', name=self.input_data['name'])
        self.add_company_metadata()
```

### Pattern 5: CLI Plugin System

Create pluggable CLI commands:

```python
from nskit.cli.app import create_cli
import typer

def create_extended_cli(backend):
    """Create CLI with custom commands."""
    app = create_cli(
        recipe_entrypoint='mycompany.recipes',
        backend=backend
    )
    
    @app.command()
    def validate(recipe_name: str):
        """Validate a recipe."""
        # Custom validation logic
        print(f"Validating {recipe_name}...")
    
    @app.command()
    def publish(recipe_name: str, version: str):
        """Publish a recipe."""
        # Custom publishing logic
        print(f"Publishing {recipe_name} {version}...")
    
    return app

# Usage
app = create_extended_cli(backend)
```

### Pattern 6: Middleware Pattern

Add middleware for logging, metrics, etc:

```python
from nskit.client import RecipeClient
from functools import wraps
import time

class InstrumentedClient:
    """Client wrapper with instrumentation."""
    
    def __init__(self, client: RecipeClient):
        self.client = client
    
    def _instrument(self, method_name):
        """Decorator for instrumentation."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start
                    print(f"{method_name} completed in {duration:.2f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start
                    print(f"{method_name} failed after {duration:.2f}s: {e}")
                    raise
            return wrapper
        return decorator
    
    def list_recipes(self):
        @self._instrument('list_recipes')
        def _list():
            return self.client.list_recipes()
        return _list()

# Usage
client = InstrumentedClient(RecipeClient(backend))
recipes = client.list_recipes()
```

### Pattern 7: Async Support

Wrap clients for async usage:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncRecipeClient:
    """Async wrapper for RecipeClient."""
    
    def __init__(self, client: RecipeClient):
        self.client = client
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def list_recipes(self):
        """Async list recipes."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.client.list_recipes
        )
    
    async def initialize_recipe(self, recipe_name: str, version: str, **kwargs):
        """Async initialize recipe."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.client.initialize_recipe(recipe_name, version, **kwargs)
        )

# Usage
async def main():
    client = AsyncRecipeClient(RecipeClient(backend))
    recipes = await client.list_recipes()
    print(recipes)

asyncio.run(main())
```

---

## Extension Points

### 1. Custom Backends

Implement `RecipeBackend` interface for custom storage:
- Cloud storage (S3, GCS, Azure Blob)
- Databases (PostgreSQL, MongoDB)
- APIs (internal recipe services)

### 2. Custom Merge Strategies

Extend `UpdateClient` for custom merge logic:
- Language-specific merging
- Semantic merging
- AI-assisted conflict resolution

### 3. Custom Discovery

Extend `DiscoveryClient` for advanced search:
- Full-text search
- Tag-based filtering
- Dependency analysis

### 4. Custom CLI Commands

Add commands to CLI via `create_cli()`:
- Validation commands
- Publishing workflows
- Analytics and reporting

### 5. Recipe Hooks

Add lifecycle hooks to recipes:
- Pre-generation validation
- Post-generation formatting
- Custom file processors

---

## Testing Patterns

### Unit Testing Clients

```python
import pytest
from unittest.mock import Mock
from nskit.client import RecipeClient

def test_list_recipes():
    # Mock backend
    backend = Mock()
    backend.list_recipes.return_value = [
        RecipeInfo(name='test', versions=['v1.0.0'])
    ]
    
    # Test client
    client = RecipeClient(backend)
    recipes = client.list_recipes()
    
    assert len(recipes) == 1
    assert recipes[0].name == 'test'
```

### Integration Testing Backends

```python
import pytest
from pathlib import Path
from nskit.client.backends import LocalBackend

@pytest.fixture
def temp_recipes(tmp_path):
    """Create temporary recipe directory."""
    recipes_dir = tmp_path / 'recipes'
    recipes_dir.mkdir()
    
    # Create test recipe
    recipe_dir = recipes_dir / 'test_recipe' / 'v1.0.0'
    recipe_dir.mkdir(parents=True)
    (recipe_dir / 'recipe.py').write_text('# Test recipe')
    
    return recipes_dir

def test_local_backend(temp_recipes):
    backend = LocalBackend(recipes_dir=temp_recipes)
    recipes = backend.list_recipes()
    
    assert len(recipes) == 1
    assert recipes[0].name == 'test_recipe'
```

### End-to-End Testing

```python
import pytest
from pathlib import Path
from nskit.client import RecipeClient, UpdateClient
from nskit.client.backends import LocalBackend

def test_full_workflow(tmp_path):
    # Setup
    backend = LocalBackend(recipes_dir=tmp_path / 'recipes')
    client = RecipeClient(backend)
    
    # Initialize project
    result = client.initialize_recipe(
        recipe_name='test',
        version='v1.0.0',
        input_data={'name': 'test-project'},
        output_path=tmp_path / 'output'
    )
    
    assert result.success
    assert (tmp_path / 'output' / '.recipe' / 'config.yml').exists()
    
    # Update project
    update_client = UpdateClient(backend)
    update_result = update_client.update_project(
        project_path=tmp_path / 'output',
        target_version='v1.1.0'
    )
    
    assert update_result.success
```

---

## Performance Optimization

### Caching Backend Results

```python
from functools import lru_cache
from nskit.client.backends.base import RecipeBackend

class CachedBackend(RecipeBackend):
    """Backend with caching."""
    
    def __init__(self, backend: RecipeBackend):
        self.backend = backend
    
    @property
    def entrypoint(self) -> str:
        return self.backend.entrypoint
    
    @lru_cache(maxsize=128)
    def list_recipes(self):
        return self.backend.list_recipes()
    
    @lru_cache(maxsize=256)
    def get_recipe_versions(self, recipe_name: str):
        return self.backend.get_recipe_versions(recipe_name)
    
    def fetch_recipe(self, recipe_name: str, version: str, target_path: Path):
        # No caching for fetch (large files)
        return self.backend.fetch_recipe(recipe_name, version, target_path)
```

### Parallel Recipe Processing

```python
from concurrent.futures import ThreadPoolExecutor
from nskit.client import RecipeClient

def process_recipes_parallel(client: RecipeClient, recipe_names: List[str]):
    """Process multiple recipes in parallel."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(client.get_recipe_versions, name)
            for name in recipe_names
        ]
        
        results = {}
        for name, future in zip(recipe_names, futures):
            results[name] = future.result()
        
        return results
```

---

## Security Best Practices

### Token Management

```python
import os
from pathlib import Path

def get_secure_token():
    """Get token from secure source."""
    # Priority order:
    # 1. Environment variable
    if token := os.getenv('GITHUB_TOKEN'):
        return token
    
    # 2. Secret file
    secret_file = Path.home() / '.secrets' / 'github_token'
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    # 3. Keyring (if available)
    try:
        import keyring
        return keyring.get_password('nskit', 'github_token')
    except ImportError:
        pass
    
    raise ValueError("No token found")
```

### Input Validation

```python
from pydantic import BaseModel, validator

class RecipeInput(BaseModel):
    """Validated recipe input."""
    
    project_name: str
    description: str
    
    @validator('project_name')
    def validate_project_name(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Project name must be alphanumeric')
        return v

# Usage
input_data = RecipeInput(
    project_name='my-project',
    description='My project'
)
```

---

## Troubleshooting

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all operations show detailed logs
client.list_recipes()
```

### Inspect Backend State

```python
# Check backend configuration
print(f"Backend type: {type(backend).__name__}")
print(f"Entrypoint: {backend.entrypoint}")

# Test backend connectivity
try:
    recipes = backend.list_recipes()
    print(f"Backend working: {len(recipes)} recipes found")
except Exception as e:
    print(f"Backend error: {e}")
```

### Debug Update Conflicts

```python
result = update_client.update_project(
    project_path=Path('./project'),
    target_version='v2.0.0',
    dry_run=True  # Preview changes
)

print(f"Files to update: {result.files_updated}")
print(f"Conflicts: {result.files_with_conflicts}")
print(f"Errors: {result.errors}")
```
