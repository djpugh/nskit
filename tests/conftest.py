"""Shared pytest fixtures and configuration.

These fixtures use autouse=False and assign to ``self`` via the ``request``
fixture so they work with unittest.TestCase classes. To use them, decorate
the test class or method with ``@pytest.mark.usefixtures("fixture_name")``.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir(request):
    """Create a temporary directory that's cleaned up after test.

    Assigns ``self.temp_dir`` on the test instance.
    """
    tmpdir = Path(tempfile.mkdtemp())
    if request.instance is not None:
        request.instance.temp_dir = tmpdir
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def git_repo(request, tmp_path):
    """Create a temporary git repository with an initial commit.

    Assigns ``self.git_repo`` on the test instance.
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True, check=True)

    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True, check=True)

    if request.instance is not None:
        request.instance.git_repo = repo_path
    return repo_path


@pytest.fixture
def sample_recipe_config(request):
    """Sample recipe configuration dict.

    Assigns ``self.sample_recipe_config`` on the test instance.
    """
    config = {
        "metadata": {
            "recipe_name": "test_recipe",
            "recipe_version": "v1.0.0",
            "docker_image": "test/recipe:v1.0.0",
            "github_repo": "test/recipe",
            "generated_at": "2026-02-28T00:00:00Z",
        }
    }
    if request.instance is not None:
        request.instance.sample_recipe_config = config
    return config


@pytest.fixture
def mock_recipe_files(request, tmp_path):
    """Create mock recipe template files in a temporary directory.

    Assigns ``self.mock_recipe_files`` on the test instance.
    """
    recipe_dir = tmp_path / "recipe"
    recipe_dir.mkdir()

    (recipe_dir / "template.txt").write_text("Hello {{name}}")
    (recipe_dir / "README.md").write_text("# {{name}}\n\n{{description}}")
    (recipe_dir / "config.json").write_text('{"version": "1.0.0"}')

    if request.instance is not None:
        request.instance.mock_recipe_files = recipe_dir
    return recipe_dir
