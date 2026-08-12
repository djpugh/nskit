"""Integration tests for built-in hooks with kwargs forwarding.

Verifies that all shipped hooks (GitInit, PrecommitInstall, CleanupHook)
continue to work correctly when called with the recipe kwarg, as happens
in Recipe.create().
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from nskit.mixer.components.file import File
from nskit.mixer.components.hook import Hook
from nskit.mixer.components.recipe import Recipe
from nskit.mixer.hooks.cleanup import CleanupHook, RemoveEmptyDirectoriesHook, RemoveEmptyFilesHook
from nskit.mixer.hooks.git import GitInit


class TestGitInitWithRecipeKwarg(unittest.TestCase):
    """GitInit hook works when called with recipe= kwarg."""

    def test_git_init_called_with_recipe_kwarg(self):
        """GitInit still works when __call__ forwards recipe kwarg."""
        hook = GitInit()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            path.mkdir()

            # Call with recipe kwarg (as Recipe.create() now does)
            result_path, result_ctx = hook(path, {}, recipe="mock_recipe")

            self.assertEqual(result_path, path)
            # Git should be initialised
            self.assertTrue((path / ".git").exists())

    def test_git_init_respects_context_branch_name(self):
        """GitInit uses git.initial_branch_name from context when provided."""
        hook = GitInit()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            path.mkdir()

            context = {"git": {"initial_branch_name": "develop"}}
            hook(path, context, recipe="mock_recipe")

            # Check the current branch name
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout.strip(), "develop")

    def test_git_init_default_branch_main(self):
        """GitInit defaults to 'main' branch."""
        hook = GitInit()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            path.mkdir()

            hook(path, {}, recipe=None)

            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            # Should be 'main' or whatever the system default is
            branch = result.stdout.strip()
            self.assertTrue(len(branch) > 0)

    def test_git_init_rejects_malicious_branch_name(self):
        """GitInit sanitises branch names that start with '-'."""
        hook = GitInit()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            path.mkdir()

            # Attempt injection via branch name
            context = {"git": {"initial_branch_name": "--exec=malicious"}}
            hook(path, context)

            # Should fall back to 'main'
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.stdout.strip(), "main")


class TestCleanupHooksWithRecipeKwarg(unittest.TestCase):
    """Cleanup hooks work when called with recipe= kwarg."""

    def test_remove_empty_files_with_recipe_kwarg(self):
        """RemoveEmptyFilesHook works when called via __call__ with recipe kwarg."""
        hook = RemoveEmptyFilesHook()
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "empty.txt").write_text("")
            (path / "notempty.txt").write_text("content")

            result_path, result_ctx = hook(path, {}, recipe="mock")

            self.assertEqual(result_path, path)
            self.assertFalse((path / "empty.txt").exists())
            self.assertTrue((path / "notempty.txt").exists())

    def test_remove_empty_dirs_with_recipe_kwarg(self):
        """RemoveEmptyDirectoriesHook works when called via __call__ with recipe kwarg."""
        hook = RemoveEmptyDirectoriesHook()
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "empty_dir").mkdir()
            (path / "full_dir").mkdir()
            (path / "full_dir" / "file.txt").write_text("content")

            result_path, result_ctx = hook(path, {}, recipe="mock")

            self.assertEqual(result_path, path)
            self.assertFalse((path / "empty_dir").exists())
            self.assertTrue((path / "full_dir").exists())

    def test_cleanup_hook_with_recipe_kwarg(self):
        """CleanupHook (combined) works when called via __call__ with recipe kwarg."""
        hook = CleanupHook()
        with TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "empty.txt").write_text("")
            (path / "empty_dir").mkdir()
            (path / "keep.txt").write_text("content")

            result_path, result_ctx = hook(path, {}, recipe="mock")

            self.assertFalse((path / "empty.txt").exists())
            self.assertFalse((path / "empty_dir").exists())
            self.assertTrue((path / "keep.txt").exists())


class TestGitInitInRecipeCreate(unittest.TestCase):
    """GitInit hook works end-to-end within Recipe.create()."""

    def test_recipe_with_git_init_creates_git_repo(self):
        """A recipe using GitInit as post_hook creates a git repo."""
        recipe = Recipe(
            name="git-test",
            post_hooks=[GitInit()],
            contents=[File(id_="readme", name="README.md", content="# Hello\n")],
        )

        with TemporaryDirectory() as tmp:
            result = recipe.create(Path(tmp))
            project_path = list(result.keys())[0]

            self.assertTrue((project_path / ".git").exists())
            self.assertTrue((project_path / "README.md").exists())
            self.assertEqual((project_path / "README.md").read_text(), "# Hello\n")


class TestCleanupHookInRecipeCreate(unittest.TestCase):
    """CleanupHook works end-to-end within Recipe.create()."""

    def test_recipe_with_cleanup_removes_empty_files(self):
        """Cleanup post-hook removes empty rendered files."""
        recipe = Recipe(
            name="cleanup-test",
            post_hooks=[CleanupHook()],
            contents=[
                File(id_="readme", name="README.md", content="# cleanup-test\n"),
                # This file renders to empty content
                File(id_="feature", name="feature.txt", content=""),
            ],
        )

        with TemporaryDirectory() as tmp:
            result = recipe.create(Path(tmp))
            project_path = list(result.keys())[0]

            self.assertTrue((project_path / "README.md").exists())
            # Empty file should be cleaned up
            self.assertFalse((project_path / "feature.txt").exists())

    def test_recipe_with_cleanup_keeps_non_empty(self):
        """Cleanup post-hook keeps non-empty rendered files."""
        recipe = Recipe(
            name="cleanup-test",
            post_hooks=[CleanupHook()],
            contents=[
                File(id_="readme", name="README.md", content="# cleanup-test\n"),
                File(id_="feature", name="feature.txt", content="feature content"),
            ],
        )

        with TemporaryDirectory() as tmp:
            result = recipe.create(Path(tmp))
            project_path = list(result.keys())[0]

            self.assertTrue((project_path / "README.md").exists())
            self.assertTrue((project_path / "feature.txt").exists())
            self.assertEqual((project_path / "feature.txt").read_text(), "feature content")


class TestHookChainWithGitAndCleanup(unittest.TestCase):
    """Multiple built-in hooks can be chained together."""

    def test_cleanup_then_git_init(self):
        """Cleanup runs first, then git init — empty files not committed."""
        recipe = Recipe(
            name="chain-test",
            post_hooks=[CleanupHook(), GitInit()],
            contents=[
                File(id_="readme", name="README.md", content="# chain-test\n"),
                File(id_="empty", name="empty.txt", content=""),
            ],
        )

        with TemporaryDirectory() as tmp:
            result = recipe.create(Path(tmp))
            project_path = list(result.keys())[0]

            # Empty file cleaned
            self.assertFalse((project_path / "empty.txt").exists())
            # Git initialised
            self.assertTrue((project_path / ".git").exists())


if __name__ == "__main__":
    unittest.main()
