"""Cleanup hooks for post-processing generated files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from nskit.mixer.components.hook import Hook


class RemoveEmptyFilesHook(Hook):
    """Post hook that removes all empty files from the generated recipe."""
    skip_gitkeep: bool = True

    def call(
        self, recipe_path: Path, context: Dict[str, Any], skip_gitkeep: bool = True
    ) -> Optional[Tuple[Path, Dict[str, Any]]]:
        """Remove all empty files from the recipe directory.

        Args:
            recipe_path: Path to the generated recipe directory
            context: Recipe context dictionary
            skip_gitkeep: If True, do not remove empty .gitkeep files

        Returns:
            Tuple of (recipe_path, context) or None if no changes needed
        """
        if not recipe_path.exists():
            return None

        empty_files_removed = []

        # Walk through all files in the recipe directory
        for root, dirs, files in os.walk(recipe_path):
            for file in files:
                file_path = Path(root) / file
                try:
                    # Check if file is empty (0 bytes)
                    if file_path.stat().st_size == 0 and not (skip_gitkeep and file_path.name == ".gitkeep"):
                        file_path.unlink()  # Remove the empty file
                        empty_files_removed.append(
                            str(file_path.relative_to(recipe_path))
                        )
                except OSError as e:
                    # Log error but continue processing other files
                    print(f"Warning: Could not process file {file_path}: {e}")
                    continue

        if empty_files_removed:
            print(f"Removed {len(empty_files_removed)} empty files:")
            for file_path in empty_files_removed:
                print(f"  - {file_path}")

        # Return the same recipe_path and context (no modifications needed)
        return recipe_path, context


class RemoveEmptyDirectoriesHook(Hook):
    """Post hook that removes all empty directories from the generated recipe."""

    def call(
        self, recipe_path: Path, context: Dict[str, Any]
    ) -> Optional[Tuple[Path, Dict[str, Any]]]:
        """Remove all empty directories from the recipe directory.

        Args:
            recipe_path: Path to the generated recipe directory
            context: Recipe context dictionary

        Returns:
            Tuple of (recipe_path, context) or None if no changes needed
        """
        if not recipe_path.exists():
            return None

        empty_dirs_removed = []

        # Walk through directories in reverse order (deepest first)
        for root, dirs, files in os.walk(recipe_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    # Check if directory is empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()  # Remove the empty directory
                        empty_dirs_removed.append(
                            str(dir_path.relative_to(recipe_path))
                        )
                except OSError as e:
                    # Log error but continue processing other directories
                    print(f"Warning: Could not process directory {dir_path}: {e}")
                    continue

        if empty_dirs_removed:
            print(f"Removed {len(empty_dirs_removed)} empty directories:")
            for dir_path in empty_dirs_removed:
                print(f"  - {dir_path}/")

        # Return the same recipe_path and context (no modifications needed)
        return recipe_path, context


class CleanupHook(Hook):
    """Combined cleanup hook that removes both empty files and directories."""

    remove_empty_files: bool = True
    remove_empty_dirs: bool = True
    skip_gitkeep: bool = True

    def call(
        self, recipe_path: Path, context: Dict[str, Any]
    ) -> Optional[Tuple[Path, Dict[str, Any]]]:
        """Clean up empty files and/or directories from the recipe directory.

        Args:
            recipe_path: Path to the generated recipe directory
            context: Recipe context dictionary
            skip_gitkeep: If True, do not remove empty .gitkeep files

        Returns:
            Tuple of (recipe_path, context) or None if no changes needed
        """
        if not recipe_path.exists():
            return None

        # Remove empty files first
        if self.remove_empty_files:
            empty_files_hook = RemoveEmptyFilesHook(skip_gitkeep=self.skip_gitkeep)
            empty_files_hook.call(recipe_path, context)

        # Then remove empty directories
        if self.remove_empty_dirs:
            empty_dirs_hook = RemoveEmptyDirectoriesHook()
            empty_dirs_hook.call(recipe_path, context)

        # Return the same recipe_path and context (no modifications needed)
        return recipe_path, context
