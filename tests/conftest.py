"""Shared pytest fixtures and configuration."""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after test."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    import subprocess
    
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        capture_output=True,
        check=True
    )
    
    return repo_path


@pytest.fixture
def sample_recipe_config():
    """Sample recipe configuration."""
    return {
        "metadata": {
            "recipe_name": "test_recipe",
            "recipe_version": "v1.0.0",
            "docker_image": "test/recipe:v1.0.0",
            "github_repo": "test/recipe",
            "generated_at": "2026-02-28T00:00:00Z"
        }
    }


@pytest.fixture
def mock_recipe_files(tmp_path):
    """Create mock recipe files."""
    recipe_dir = tmp_path / "recipe"
    recipe_dir.mkdir()
    
    # Create sample files
    (recipe_dir / "template.txt").write_text("Hello {{name}}")
    (recipe_dir / "README.md").write_text("# {{name}}\n\n{{description}}")
    (recipe_dir / "config.json").write_text('{"version": "1.0.0"}')
    
    return recipe_dir


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_git: mark test as requiring git"
    )
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
