# Testing Guide

Comprehensive testing setup for nskit with functional, integration, and property-based tests.

## Quick Start

```bash
# Run all tests
cd nskit
uv run pytest

# Run specific test suite
uv run pytest tests/test_recipe_client.py -v

# Run with coverage
uv run pytest --cov=nskit --cov-report=html

# Use test runner script
./run_tests.sh
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_recipe_client.py    # RecipeClient functional tests
├── test_update_client.py    # UpdateClient functional tests
├── test_github_backend.py   # GitHub backend with mocked API
├── test_integration.py      # End-to-end integration tests
└── test_properties.py       # Property-based tests (Hypothesis)
```

## Test Categories

### 1. Functional Tests (Unit Tests)

Fast tests with mocked dependencies.

**test_recipe_client.py**
- List recipes
- Get recipe versions
- Initialize recipes

**test_update_client.py**
- Check for updates
- Update validation (git status, uncommitted changes)
- Dry-run mode

**test_github_backend.py**
- GitHub API mocking
- List recipes from GitHub
- Get versions from releases
- Fetch recipe archives
- Error handling

**Run:**
```bash
uv run pytest tests/ -m "not integration" -v
```

### 2. Integration Tests

End-to-end tests with real file operations.

**test_integration.py**
- Complete workflow: discover → init → update
- Update preserves user changes
- Dry-run doesn't modify files
- Multi-version recipe handling

**Run:**
```bash
uv run pytest tests/test_integration.py -v
```

### 3. Property-Based Tests

Hypothesis-powered tests for input validation.

**test_properties.py**
- RecipeInfo model validation
- UpdateResult model validation
- RepositoryInfo model validation
- Input data validation
- Backend configuration validation

**Run:**
```bash
uv run pytest tests/test_properties.py -v
```

## Test Markers

```bash
# Skip integration tests
uv run pytest -m "not integration"

# Skip slow tests
uv run pytest -m "not slow"

# Only integration tests
uv run pytest -m integration

# Tests requiring git
uv run pytest -m requires_git

# Tests requiring network
uv run pytest -m requires_network
```

## Coverage

```bash
# Generate coverage report
uv run pytest --cov=nskit --cov-report=html

# View report
open htmlcov/index.html

# Terminal report
uv run pytest --cov=nskit --cov-report=term-missing
```

## Fixtures

### Shared Fixtures (conftest.py)

```python
# Temporary directory
def test_example(temp_dir):
    file = temp_dir / "test.txt"
    file.write_text("test")

# Git repository
def test_example(git_repo):
    assert (git_repo / ".git").exists()

# Sample recipe config
def test_example(sample_recipe_config):
    assert sample_recipe_config["metadata"]["recipe_name"] == "test_recipe"

# Mock recipe files
def test_example(mock_recipe_files):
    assert (mock_recipe_files / "template.txt").exists()
```

### Test-Specific Fixtures

```python
# Mock backend
@pytest.fixture
def mock_backend():
    backend = Mock()
    backend.list_recipes.return_value = [...]
    return backend

# Mock project
@pytest.fixture
def mock_project(tmp_path):
    # Create project with recipe config
    return project_path
```

## Writing Tests

### Functional Test Example

```python
def test_list_recipes(mock_backend):
    """Test listing recipes."""
    client = RecipeClient(mock_backend)
    recipes = client.list_recipes()
    
    assert len(recipes) == 2
    assert recipes[0].name == "python_package"
    mock_backend.list_recipes.assert_called_once()
```

### Integration Test Example

```python
@pytest.mark.integration
def test_full_workflow(backend, tmp_path):
    """Test complete workflow."""
    # Discover
    discovery = DiscoveryClient(backend)
    recipes = discovery.discover_recipes()
    
    # Initialize
    client = RecipeClient(backend)
    result = client.initialize_recipe(...)
    
    # Update
    update_client = UpdateClient(backend)
    update_result = update_client.update_project(...)
    
    assert update_result.success
```

### Property-Based Test Example

```python
from hypothesis import given, strategies as st

@given(
    name=st.text(min_size=1, max_size=50),
    versions=st.lists(st.text(), min_size=0, max_size=10)
)
def test_recipe_info_creation(name, versions):
    """Test RecipeInfo with any valid inputs."""
    recipe = RecipeInfo(name=name, versions=versions)
    assert recipe.name == name
```

## Mocking GitHub API

```python
@pytest.fixture
def mock_ghapi():
    with patch('nskit.cli.backends.github.GhApi') as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        
        # Mock repos
        mock_client.repos.list_for_org.return_value = [...]
        
        # Mock releases
        mock_client.repos.list_releases.return_value = [...]
        
        yield mock_client

def test_github_backend(mock_ghapi):
    backend = GitHubBackend(org="testorg", token="test")
    recipes = backend.list_recipes()
    assert len(recipes) > 0
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - name: Run tests
        run: |
          cd nskit
          uv run pytest --cov=nskit --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tests

```bash
# Run with verbose output
uv run pytest -vv

# Stop on first failure
uv run pytest -x

# Run specific test
uv run pytest tests/test_recipe_client.py::TestRecipeClient::test_list_recipes

# Show print statements
uv run pytest -s

# Drop into debugger on failure
uv run pytest --pdb
```

## Performance Testing

```bash
# Show slowest tests
uv run pytest --durations=10

# Parallel execution
uv run pytest -n auto
```

## Test Data

### Sample Recipe Structure

```
recipes/
  python_package/
    v1.0.0/
      template.txt
      README.md
    v1.1.0/
      template.txt
      README.md
      CHANGELOG.md
```

### Sample Recipe Config

```yaml
metadata:
  recipe_name: python_package
  recipe_version: v1.0.0
  docker_image: test/python_package:v1.0.0
  github_repo: test/python_package
```

## Best Practices

1. **Use fixtures** - Reuse setup code
2. **Mock external dependencies** - GitHub API, Docker, etc.
3. **Test edge cases** - Empty lists, None values, errors
4. **Use property-based tests** - Validate input handling
5. **Mark slow tests** - Use markers for CI optimization
6. **Clean up resources** - Use tmp_path, context managers
7. **Test error paths** - Not just happy paths
8. **Keep tests fast** - Mock I/O, use small datasets

## Troubleshooting

### Tests fail with import errors
```bash
# Install test dependencies
uv pip install -e ".[dev-test]"
```

### Git tests fail
```bash
# Ensure git is configured
git config --global user.email "test@example.com"
git config --global user.name "Test User"
```

### Coverage not working
```bash
# Install coverage plugin
uv pip install pytest-cov
```

### Hypothesis tests too slow
```python
# Reduce example count
from hypothesis import settings

@settings(max_examples=50)
@given(...)
def test_example(...):
    pass
```
