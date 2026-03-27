"""End-to-end workflow tests: init → customise → update for both engine types.

Exercises the full user journey through the RecipeClient and UpdateClient
with real recipe execution (LocalEngine) and mocked Docker execution.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from nskit.client.backends.local import LocalBackend
from nskit.client.config import ConfigManager, RecipeConfig, RecipeMetadata
from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.models import RecipeResult
from nskit.client.recipes import RecipeClient
from nskit.client.update import UpdateClient
from nskit.common.models.diff import DiffMode

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RECIPE_PARAMS = {
    "name": "e2e.test.pkg",
    "repo": {
        "owner": "Test Owner",
        "email": "test@example.com",
        "description": "E2E workflow test",
        "url": "https://example.com",
    },
}


def _git_init(path: Path) -> None:
    """Configure git user and make an initial commit.

    The recipe's git hook already runs ``git init``, so we only need
    to configure the user and commit.  We use ``--no-verify`` to skip
    pre-commit hooks that the recipe may have installed.
    """
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit", "--no-verify"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def _make_local_backend() -> Mock:
    """Create a mock backend suitable for LocalEngine."""
    backend = Mock()
    backend.entrypoint = "nskit.recipes"
    backend.get_image_url = Mock(return_value="img:v1")
    backend.pull_image = Mock()
    backend.get_recipe_versions = Mock(return_value=["v1.0.0", "v2.0.0"])
    return backend


def _write_recipe_config(project_dir: Path, version: str = "v1.0.0") -> None:
    """Write a .recipe/config.yml so UpdateClient can load it."""
    cfg = RecipeConfig(
        input=_RECIPE_PARAMS,
        metadata=RecipeMetadata(
            recipe_name="python_package",
            docker_image=f"ghcr.io/org/python_package:{version}",
        ),
    )
    ConfigManager(project_dir).save_config(cfg)


# ---------------------------------------------------------------------------
# LocalEngine: init → customise → update
# ---------------------------------------------------------------------------


class TestLocalEngineWorkflow(unittest.TestCase):
    """Full init → customise → update cycle using LocalEngine."""

    def test_init_then_update_preserves_user_changes(self) -> None:
        """Init a project, customise a file, then update.

        The update should apply template changes while preserving
        user modifications to other parts of the file.
        """
        backend = _make_local_backend()
        engine = LocalEngine()

        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "my-project"

            # --- Step 1: Init ---
            client = RecipeClient(backend, engine=engine)
            result = client.initialize_recipe(
                recipe="python_package",
                version="v1.0.0",
                parameters=_RECIPE_PARAMS,
                output_dir=project_dir,
            )
            self.assertTrue(result.success, f"Init failed: {result.errors}")
            self.assertTrue(project_dir.exists())

            readme = project_dir / "README.md"
            self.assertTrue(readme.exists(), "README.md should be generated")

            # --- Step 2: Persist recipe config + git init ---
            _write_recipe_config(project_dir, "v1.0.0")
            _git_init(project_dir)

            # --- Step 3: User customises a file ---
            original_readme = readme.read_text()
            readme.write_text(original_readme + "\n\n## My Custom Section\n")
            subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "User customisation", "--no-verify"],
                cwd=project_dir,
                capture_output=True,
                check=True,
            )

            # --- Step 4: Update (same recipe, same version = no-op) ---
            update_client = UpdateClient(backend, engine=engine)
            update_result = update_client.update_project(
                project_path=project_dir,
                target_version="v1.0.0",
                diff_mode=DiffMode.THREE_WAY,
                dry_run=False,
            )

            # Same version → no meaningful changes
            self.assertTrue(
                update_result.success or len(update_result.errors) == 0,
                f"Update failed: {update_result.errors}",
            )

            # User content should still be present
            self.assertIn("My Custom Section", readme.read_text())

    def test_init_creates_expected_files(self) -> None:
        """LocalEngine init produces the expected project structure."""
        backend = _make_local_backend()
        engine = LocalEngine()

        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "structure-test"
            client = RecipeClient(backend, engine=engine)
            result = client.initialize_recipe(
                recipe="python_package",
                version="v1.0.0",
                parameters=_RECIPE_PARAMS,
                output_dir=project_dir,
            )

            self.assertTrue(result.success, f"Init failed: {result.errors}")

            # Check key files exist
            expected_files = ["pyproject.toml", "README.md"]
            for fname in expected_files:
                matches = list(project_dir.rglob(fname))
                self.assertTrue(
                    len(matches) > 0,
                    f"Expected {fname} in generated project",
                )

    def test_dry_run_update_does_not_modify_files(self) -> None:
        """Dry-run update analyses changes without writing."""
        backend = _make_local_backend()
        engine = LocalEngine()

        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "dryrun-test"
            client = RecipeClient(backend, engine=engine)
            result = client.initialize_recipe(
                recipe="python_package",
                version="v1.0.0",
                parameters=_RECIPE_PARAMS,
                output_dir=project_dir,
            )
            self.assertTrue(result.success)

            _write_recipe_config(project_dir, "v1.0.0")
            _git_init(project_dir)

            # Snapshot file contents
            files_before = {
                str(p.relative_to(project_dir)): p.read_bytes() for p in project_dir.rglob("*") if p.is_file()
            }

            update_client = UpdateClient(backend, engine=engine)
            update_client.update_project(
                project_path=project_dir,
                target_version="v1.0.0",
                diff_mode=DiffMode.THREE_WAY,
                dry_run=True,
            )

            # Files should be unchanged
            for rel, content in files_before.items():
                current = (project_dir / rel).read_bytes()
                self.assertEqual(
                    current,
                    content,
                    f"Dry-run modified {rel}",
                )


# ---------------------------------------------------------------------------
# DockerEngine: init → update (mocked container execution)
# ---------------------------------------------------------------------------


class TestDockerEngineWorkflow(unittest.TestCase):
    """Full init → update cycle using DockerEngine with mocked execution.

    These tests verify the orchestration path through DockerEngine
    without requiring a running Docker daemon.
    """

    def _mock_docker_execute(
        self,
        recipe,
        version,
        parameters,
        output_dir,
        image_url=None,
        entrypoint=None,
    ) -> RecipeResult:
        """Simulate Docker engine execution by writing files directly."""
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "README.md").write_text(f"# {parameters.get('name', 'project')}\n\nVersion {version}\n")
        (output_dir / "pyproject.toml").write_text(
            f'[project]\nname = "{parameters.get("name", "pkg")}"\nversion = "{version}"\n'
        )
        return RecipeResult(
            success=True,
            project_path=output_dir,
            recipe_name=recipe,
            recipe_version=version,
            files_created=[output_dir / "README.md", output_dir / "pyproject.toml"],
        )

    def test_docker_init_then_update(self) -> None:
        """Docker-based init followed by update with mocked execution."""
        backend = _make_local_backend()
        engine = DockerEngine(skip_pull=True)

        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "docker-project"

            # Mock the engine's execute method
            with patch.object(engine, "execute", side_effect=self._mock_docker_execute):
                client = RecipeClient(backend, engine=engine)
                result = client.initialize_recipe(
                    recipe="python_package",
                    version="v1.0.0",
                    parameters=_RECIPE_PARAMS,
                    output_dir=project_dir,
                )

            self.assertTrue(result.success, f"Docker init failed: {result.errors}")
            self.assertTrue((project_dir / "README.md").exists())
            self.assertTrue((project_dir / "pyproject.toml").exists())

            # Setup for update
            _write_recipe_config(project_dir, "v1.0.0")
            _git_init(project_dir)

            # User customises
            readme = project_dir / "README.md"
            readme.write_text(readme.read_text() + "\n## User Notes\n")
            subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "User changes", "--no-verify"],
                cwd=project_dir,
                capture_output=True,
                check=True,
            )

            # Update with mocked engine
            update_engine = DockerEngine(skip_pull=True)
            with patch.object(update_engine, "execute", side_effect=self._mock_docker_execute):
                update_client = UpdateClient(backend, engine=update_engine)
                update_result = update_client.update_project(
                    project_path=project_dir,
                    target_version="v2.0.0",
                    diff_mode=DiffMode.THREE_WAY,
                    dry_run=False,
                )

            self.assertTrue(
                update_result.success or len(update_result.errors) == 0,
                f"Docker update failed: {update_result.errors}",
            )

    def test_docker_two_way_update(self) -> None:
        """Docker-based 2-way update overwrites files."""
        backend = _make_local_backend()
        engine = DockerEngine(skip_pull=True)

        with TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "docker-2way"

            with patch.object(engine, "execute", side_effect=self._mock_docker_execute):
                client = RecipeClient(backend, engine=engine)
                result = client.initialize_recipe(
                    recipe="python_package",
                    version="v1.0.0",
                    parameters=_RECIPE_PARAMS,
                    output_dir=project_dir,
                )

            self.assertTrue(result.success)
            _write_recipe_config(project_dir, "v1.0.0")
            _git_init(project_dir)

            update_engine = DockerEngine(skip_pull=True)
            with patch.object(update_engine, "execute", side_effect=self._mock_docker_execute):
                update_client = UpdateClient(backend, engine=update_engine)
                update_result = update_client.update_project(
                    project_path=project_dir,
                    target_version="v2.0.0",
                    diff_mode=DiffMode.TWO_WAY,
                    dry_run=False,
                )

            self.assertTrue(
                update_result.success or len(update_result.errors) == 0,
                f"2-way update failed: {update_result.errors}",
            )

            # 2-way should overwrite with new version content
            readme_content = (project_dir / "README.md").read_text()
            self.assertIn("v2.0.0", readme_content)


if __name__ == "__main__":
    unittest.main()
