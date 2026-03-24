"""Update client for recipe updates with 3-way merge."""
from pathlib import Path
from typing import Optional

from nskit.client.diff import DiffEngine
from nskit.client.diff.models import DiffMode, MergeResult
from nskit.client.utils.git import GitUtils
from nskit.client.models import UpdateResult


class UpdateClient:
    """Pure Python client for recipe updates (no CLI dependencies)."""

    def __init__(self, backend: 'RecipeBackend'):
        """Initialize update client.
        
        Args:
            backend: Backend for fetching recipe versions
        """
        self.backend = backend

    def check_update_available(self, project_path: Path) -> Optional[str]:
        """Check if update is available for project.
        
        Args:
            project_path: Path to project
            
        Returns:
            Latest version if available, None otherwise
        """
        from nskit.mixer.components import RecipeConfig

        config_path = project_path / ".recipe" / "config.yml"
        if not config_path.exists():
            return None

        try:
            config = RecipeConfig.load_from_file(config_path)
            if not config.metadata:
                return None

            recipe_name = config.metadata.recipe_name
            current_version = config.metadata.recipe_version or recipe_name
            versions = self.backend.get_recipe_versions(recipe_name)

            if versions and versions[-1] != current_version:
                return versions[-1]
        except Exception:
            pass

        return None

    def update_project(
        self,
        project_path: Path,
        target_version: str,
        diff_mode: DiffMode = DiffMode.THREE_WAY,
        dry_run: bool = False,
    ) -> UpdateResult:
        """Update project to target version.
        
        Args:
            project_path: Path to project
            target_version: Target version to update to
            diff_mode: Diff mode (2-way or 3-way)
            dry_run: If True, don't make changes
            
        Returns:
            Update result with conflicts and errors
        """
        import tempfile

        from nskit.mixer.components import RecipeConfig

        errors = []
        warnings = []

        # Validate git status
        git_utils = GitUtils(project_path)
        if not git_utils.is_git_repository():
            errors.append("Project is not a git repository")
            return UpdateResult(success=False, errors=errors)

        if git_utils.has_uncommitted_changes():
            errors.append("Project has uncommitted changes. Commit or stash them first.")
            return UpdateResult(success=False, errors=errors)

        # Load current recipe config
        config_path = project_path / ".recipe" / "config.yml"
        if not config_path.exists():
            errors.append("No recipe config found. Is this a recipe-generated project?")
            return UpdateResult(success=False, errors=errors)

        try:
            config = RecipeConfig.load_from_file(config_path)
            if not config.metadata:
                errors.append("Recipe config missing metadata")
                return UpdateResult(success=False, errors=errors)

            recipe_name = config.metadata.recipe_name

            # Fetch new recipe version
            with tempfile.TemporaryDirectory() as temp_dir:
                new_recipe_path = self.backend.fetch_recipe(
                    recipe_name, target_version, Path(temp_dir)
                )

                # Perform merge
                merge_result = self._merge_changes(
                    project_path=project_path,
                    new_recipe_path=new_recipe_path,
                    git_utils=git_utils,
                    diff_mode=diff_mode,
                    dry_run=dry_run,
                )

                return UpdateResult(
                    success=len(merge_result.errors) == 0,
                    files_updated=merge_result.clean_merges,
                    files_with_conflicts=merge_result.conflicts,
                    clean_merges=merge_result.clean_merges,
                    errors=merge_result.errors,
                    warnings=warnings,
                )

        except Exception as e:
            errors.append(f"Update failed: {e}")
            return UpdateResult(success=False, errors=errors)

    def _merge_changes(
        self,
        project_path: Path,
        new_recipe_path: Path,
        git_utils: GitUtils,
        diff_mode: DiffMode,
        dry_run: bool,
    ) -> MergeResult:
        """Merge changes from new recipe version.
        
        Args:
            project_path: Current project path
            new_recipe_path: New recipe path
            git_utils: Git utilities instance
            diff_mode: Diff mode
            dry_run: If True, don't write changes
            
        Returns:
            Merge result
        """
        import tempfile

        from nskit.mixer.components import RecipeConfig

        clean_merges = []
        conflicts = []
        errors = []

        # Load current config to get base version
        config_path = project_path / ".recipe" / "config.yml"
        config = RecipeConfig.load_from_file(config_path)

        if diff_mode == DiffMode.THREE_WAY and config.metadata:
            # Get base version for 3-way merge
            base_version = config.metadata.recipe_version

            with tempfile.TemporaryDirectory() as temp_dir:
                # Fetch base version
                base_path = self.backend.fetch_recipe(
                    config.metadata.recipe_name,
                    base_version,
                    Path(temp_dir) / "base",
                )

                # Perform 3-way merge
                result = self._three_way_merge(
                    base_path=base_path,
                    current_path=project_path,
                    new_path=new_recipe_path,
                    git_utils=git_utils,
                    dry_run=dry_run,
                )
                return result
        else:
            # Perform 2-way merge
            result = self._two_way_merge(
                current_path=project_path,
                new_path=new_recipe_path,
                dry_run=dry_run,
            )
            return result

    def _three_way_merge(
        self,
        base_path: Path,
        current_path: Path,
        new_path: Path,
        git_utils: GitUtils,
        dry_run: bool,
    ) -> MergeResult:
        """Perform 3-way merge using git merge-file.
        
        Args:
            base_path: Base version path
            current_path: Current project path
            new_path: New recipe path
            git_utils: Git utilities
            dry_run: If True, don't write changes
            
        Returns:
            Merge result
        """
        clean_merges = []
        conflicts = []
        errors = []

        # Get files to merge
        diff_engine = DiffEngine()
        diff_result = diff_engine.extract_diff(base_path, new_path)

        # Process each modified file
        for file_diff in diff_result.modified_files:
            base_file = base_path / file_diff.relative_path
            current_file = current_path / file_diff.relative_path
            new_file = new_path / file_diff.relative_path

            if not current_file.exists():
                # File was deleted by user, skip
                continue

            try:
                # Read file contents
                base_content = base_file.read_text() if base_file.exists() else ""
                current_content = current_file.read_text()
                new_content = new_file.read_text()
                
                # Use git merge-file for 3-way merge
                merged_content, has_conflicts = git_utils.merge_file(
                    base_content, current_content, new_content
                )

                if has_conflicts:
                    conflicts.append(str(file_diff.relative_path))
                else:
                    clean_merges.append(str(file_diff.relative_path))

                if not dry_run and merged_content:
                    current_file.write_text(merged_content)

            except Exception as e:
                errors.append(f"Failed to merge {file_diff.relative_path}: {e}")

        # Handle added files
        for file_diff in diff_result.added_files:
            new_file = new_path / file_diff.relative_path
            current_file = current_path / file_diff.relative_path

            if not dry_run:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_bytes(new_file.read_bytes())

            clean_merges.append(str(file_diff.relative_path))

        return MergeResult(
            clean_merges=clean_merges,
            conflicts=conflicts,
            errors=errors,
        )

    def _two_way_merge(
        self,
        current_path: Path,
        new_path: Path,
        dry_run: bool,
    ) -> MergeResult:
        """Perform 2-way merge (simple overwrite).
        
        Args:
            current_path: Current project path
            new_path: New recipe path
            dry_run: If True, don't write changes
            
        Returns:
            Merge result
        """
        from nskit.client.diff import DiffEngine

        clean_merges = []

        diff_engine = DiffEngine()
        diff_result = diff_engine.extract_diff(current_path, new_path)

        # Copy all changed files
        for file_diff in diff_result.modified_files + diff_result.added_files:
            new_file = new_path / file_diff.relative_path
            current_file = current_path / file_diff.relative_path

            if not dry_run:
                current_file.parent.mkdir(parents=True, exist_ok=True)
                current_file.write_bytes(new_file.read_bytes())

            clean_merges.append(str(file_diff.relative_path))

        return MergeResult(
            clean_merges=clean_merges,
            conflicts=[],
            errors=[],
        )
