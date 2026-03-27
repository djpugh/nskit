"""Unit tests for UpdateClient."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from nskit.client.config import ConfigManager, RecipeConfig, RecipeMetadata
from nskit.client.exceptions import GitStatusError
from nskit.client.models import RecipeInfo, RecipeResult, UpdateResult
from nskit.client.update import UpdateClient
from nskit.common.models.diff import DiffMode


def _init_git_repo(path: Path) -> None:
    """Initialise a git repo with an initial commit."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
    )
    (path / "placeholder").write_text("init")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        capture_output=True,
    )


class TestCheckUpdateAvailable(unittest.TestCase):
    """Tests for UpdateClient.check_update_available."""

    def test_returns_none_when_not_recipe_based(self) -> None:
        """Returns None when project has no recipe config."""
        backend = MagicMock()
        client = UpdateClient(backend)

        with TemporaryDirectory() as tmp:
            result = client.check_update_available(Path(tmp))
            self.assertIsNone(result)

    def test_returns_version_when_update_available(self) -> None:
        """Returns new version string when an update exists."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0", "2.0.0"]

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Write a config file
            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={"name": "test"},
                metadata=RecipeMetadata(
                    recipe_name="my-recipe",
                    docker_image="ghcr.io/org/my-recipe:1.0.0",
                ),
            )
            config_mgr.save_config(config)

            client = UpdateClient(backend)
            result = client.check_update_available(tmp_path)
            self.assertEqual(result, "2.0.0")

    def test_returns_none_when_already_latest(self) -> None:
        """Returns None when project is already on the latest version."""
        backend = MagicMock()
        backend.get_recipe_versions.return_value = ["1.0.0"]

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={},
                metadata=RecipeMetadata(
                    recipe_name="my-recipe",
                    docker_image="ghcr.io/org/my-recipe:1.0.0",
                ),
            )
            config_mgr.save_config(config)

            client = UpdateClient(backend)
            result = client.check_update_available(tmp_path)
            self.assertIsNone(result)


class TestUpdateProjectValidation(unittest.TestCase):
    """Tests for UpdateClient.update_project git validation."""

    def test_raises_on_non_git_repo(self) -> None:
        """Raises GitStatusError when project is not a git repo."""
        backend = MagicMock()
        engine = MagicMock()
        client = UpdateClient(backend, engine)

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Write config so it gets past config loading
            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={},
                metadata=RecipeMetadata(
                    recipe_name="r",
                    docker_image="img:1.0.0",
                ),
            )
            config_mgr.save_config(config)

            with self.assertRaises(GitStatusError):
                client.update_project(tmp_path, "2.0.0")

    def test_raises_on_dirty_working_tree(self) -> None:
        """Raises GitStatusError when there are uncommitted changes."""
        backend = MagicMock()
        engine = MagicMock()
        client = UpdateClient(backend, engine)

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_git_repo(tmp_path)

            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={},
                metadata=RecipeMetadata(
                    recipe_name="r",
                    docker_image="img:1.0.0",
                ),
            )
            config_mgr.save_config(config)
            # Dirty the working tree (config file is untracked)

            with self.assertRaises(GitStatusError):
                client.update_project(tmp_path, "2.0.0")


class TestUpdateProjectDryRun(unittest.TestCase):
    """Tests for UpdateClient.update_project dry-run mode."""

    def test_dry_run_does_not_write_files(self) -> None:
        """Dry-run mode analyses changes without modifying the project."""
        backend = MagicMock()
        backend.get_image_url.return_value = "ghcr.io/org/recipe:2.0.0"
        engine = MagicMock()

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_git_repo(tmp_path)

            # Write and commit config
            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={"name": "test"},
                metadata=RecipeMetadata(
                    recipe_name="recipe",
                    docker_image="ghcr.io/org/recipe:1.0.0",
                ),
            )
            config_mgr.save_config(config)
            subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "add config"],
                cwd=tmp,
                capture_output=True,
            )

            # Write a project file and commit
            (tmp_path / "readme.md").write_text("original")
            subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "add readme"],
                cwd=tmp,
                capture_output=True,
            )

            client = UpdateClient(backend, engine)

            # Mock ProjectGenerator to return temp dirs with changed files
            with TemporaryDirectory() as old_tmp, TemporaryDirectory() as new_tmp:
                old_path = Path(old_tmp)
                new_path = Path(new_tmp)
                (old_path / "readme.md").write_text("original")
                (new_path / "readme.md").write_text("updated by template")

                with patch("nskit.client.update.ProjectGenerator") as mock_pg_cls:
                    mock_pg = mock_pg_cls.return_value
                    mock_pg.generate_project_states.return_value = (
                        tmp_path,
                        old_path,
                        new_path,
                    )
                    mock_pg.cleanup_states = MagicMock()

                    client.update_project(
                        tmp_path,
                        "2.0.0",
                        dry_run=True,
                    )

            # File should remain unchanged in dry-run
            self.assertEqual(
                (tmp_path / "readme.md").read_text(),
                "original",
            )


class TestUpdateProjectNoEngine(unittest.TestCase):
    """Tests for UpdateClient.update_project without an engine."""

    def test_returns_error_without_engine(self) -> None:
        """Returns error result when no engine is configured."""
        backend = MagicMock()
        client = UpdateClient(backend, engine=None)

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _init_git_repo(tmp_path)

            config_mgr = ConfigManager(tmp_path)
            config = RecipeConfig(
                input={},
                metadata=RecipeMetadata(
                    recipe_name="r",
                    docker_image="img:1.0.0",
                ),
            )
            config_mgr.save_config(config)
            subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "init config"],
                cwd=tmp,
                capture_output=True,
            )

            result = client.update_project(tmp_path, "2.0.0")
            self.assertFalse(result.success)
            self.assertTrue(
                any("engine" in e.lower() for e in result.errors),
            )


if __name__ == "__main__":
    unittest.main()
