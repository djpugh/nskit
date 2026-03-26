"""Update client for recipe updates with 3-way merge."""

from __future__ import annotations

from pathlib import Path

from nskit.client.backends.base import RecipeBackend
from nskit.client.config import ConfigManager
from nskit.client.diff.engine import DiffEngine
from nskit.client.diff.file_discovery import FileDiscovery
from nskit.client.engines.base import RecipeEngine
from nskit.client.exceptions import GitStatusError, UpdateError
from nskit.client.models import UpdateResult
from nskit.client.project_generator import ProjectGenerator
from nskit.client.utils.git import GitUtils
from nskit.client.version_resolver import VersionResolver
from nskit.common.models.diff import DiffMode, MergeResult


class UpdateClient:
    """Pure Python client for recipe updates (no CLI dependencies).

    Args:
        backend: Backend for fetching recipe versions.
        engine: Optional recipe engine for project generation.
        config_dir: Config directory name (default ``.recipe``).
        config_filename: Config file name (default ``config.yml``).
    """

    def __init__(
        self,
        backend: RecipeBackend,
        engine: RecipeEngine | None = None,
        config_dir: str = ".recipe",
        config_filename: str = "config.yml",
    ) -> None:
        self.backend = backend
        self.engine = engine
        self.config_dir = config_dir
        self.config_filename = config_filename

    def check_update_available(self, project_path: Path) -> str | None:
        """Check if an update is available for the project.

        Args:
            project_path: Path to the project.

        Returns:
            Latest version string if an update is available, ``None``
            otherwise.
        """
        config_mgr = ConfigManager(project_path, self.config_dir, self.config_filename)
        if not config_mgr.is_recipe_based():
            return None

        try:
            config = config_mgr.load_config()
            if config.metadata is None:
                return None

            resolver = VersionResolver(self.backend)
            current_image = config.metadata.docker_image
            # Extract current version from image tag
            current_version = current_image.rsplit(":", 1)[-1] if ":" in current_image else "latest"
            update_needed, resolved = resolver.check_update_needed(config.metadata.recipe_name, current_version)
            if update_needed:
                return resolved
        except Exception:  # nosec B110
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
            project_path: Path to the project.
            target_version: Target version to update to.
            diff_mode: Diff mode (2-way or 3-way).
            dry_run: If ``True``, analyse changes without writing files.

        Returns:
            Update result with conflicts and errors.
        """
        # Validate git status
        git_utils = GitUtils(project_path)
        if not git_utils.is_git_repository():
            raise GitStatusError("Project is not a git repository")

        if git_utils.has_uncommitted_changes():
            raise GitStatusError("Project has uncommitted changes. Commit or stash them first.")

        config_mgr = ConfigManager(project_path, self.config_dir, self.config_filename)
        config = config_mgr.load_config()

        if config.metadata is None:
            return UpdateResult(
                success=False,
                errors=["Recipe configuration missing metadata"],
            )

        if self.engine is None:
            return UpdateResult(
                success=False,
                errors=["No recipe engine configured for project generation"],
            )

        generator = ProjectGenerator(self.backend, self.engine)
        file_discovery = FileDiscovery()
        diff_engine = DiffEngine(file_discovery=file_discovery)

        old_fresh = None
        new_fresh = None
        try:
            _, old_fresh, new_fresh = generator.generate_project_states(config, target_version, project_path, diff_mode)

            merge_result = self._extract_and_process_changes(
                project_path=project_path,
                old_fresh=old_fresh,
                new_fresh=new_fresh,
                diff_engine=diff_engine,
                git_utils=git_utils,
                diff_mode=diff_mode,
                dry_run=dry_run,
            )

            result = UpdateResult(
                success=len(merge_result.errors) == 0,
                files_updated=merge_result.clean_merges,
                files_with_conflicts=merge_result.conflicts,
                clean_merges=merge_result.clean_merges,
                errors=merge_result.errors,
            )

            if result.success and not dry_run:
                config_mgr.update_config_version(target_version, config.metadata.recipe_name)

            return result

        except UpdateError:
            raise
        except Exception as exc:
            return UpdateResult(success=False, errors=[f"Update failed: {exc}"])
        finally:
            paths_to_clean = [p for p in [old_fresh, new_fresh] if p is not None]
            if paths_to_clean:
                generator.cleanup_states(*paths_to_clean)

    def _extract_and_process_changes(
        self,
        project_path: Path,
        old_fresh: Path | None,
        new_fresh: Path,
        diff_engine: DiffEngine,
        git_utils: GitUtils,
        diff_mode: DiffMode,
        dry_run: bool,
    ) -> MergeResult:
        """Extract diffs and process file-level merges.

        Args:
            project_path: Current project path.
            old_fresh: Base version path (``None`` for 2-way).
            new_fresh: Target version path.
            diff_engine: Diff engine instance.
            git_utils: Git utilities instance.
            diff_mode: Comparison mode.
            dry_run: Whether to skip file writes.

        Returns:
            Merge result with clean merges, conflicts, and errors.
        """
        clean_merges: list[str] = []
        conflicts: list[str] = []
        errors: list[str] = []

        if diff_mode == DiffMode.THREE_WAY and old_fresh is not None:
            diff_result = diff_engine.extract_diff(old_fresh, new_fresh, diff_mode)

            for file_diff in diff_result.modified_files:
                rel = str(file_diff.relative_path)
                result = self._process_single_file(
                    project_path,
                    old_fresh,
                    new_fresh,
                    rel,
                    git_utils,
                    dry_run,
                    three_way=True,
                )
                if result == "clean":
                    clean_merges.append(rel)
                elif result == "conflict":
                    conflicts.append(rel)
                else:
                    errors.append(result)

            for file_diff in diff_result.added_files:
                rel = str(file_diff.relative_path)
                target_file = new_fresh / rel
                dest_file = project_path / rel
                if not dry_run:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    dest_file.write_bytes(target_file.read_bytes())
                clean_merges.append(rel)

        else:
            # 2-way: compare current project against target
            diff_result = diff_engine.extract_diff(project_path, new_fresh, DiffMode.TWO_WAY)

            for file_diff in diff_result.modified_files + diff_result.added_files:
                rel = str(file_diff.relative_path)
                source = new_fresh / rel
                dest = project_path / rel
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(source.read_bytes())
                clean_merges.append(rel)

        return MergeResult(
            clean_merges=clean_merges,
            conflicts=conflicts,
            errors=errors,
        )

    def _process_single_file(
        self,
        project_path: Path,
        old_fresh: Path,
        new_fresh: Path,
        relative_path: str,
        git_utils: GitUtils,
        dry_run: bool,
        three_way: bool = True,
    ) -> str:
        """Process a single file for merge.

        Returns:
            ``"clean"`` for clean merge, ``"conflict"`` for conflicts,
            or an error message string.
        """
        base_file = old_fresh / relative_path
        current_file = project_path / relative_path
        new_file = new_fresh / relative_path

        if not current_file.exists():
            # User deleted the file — skip
            return "clean"

        try:
            # Check for binary files
            if self._is_binary(current_file) or self._is_binary(new_file):
                base_bytes = base_file.read_bytes() if base_file.exists() else b""
                current_bytes = current_file.read_bytes()
                new_bytes = new_file.read_bytes()

                if current_bytes != base_bytes and new_bytes != base_bytes:
                    # Both sides modified a binary file
                    if not dry_run:
                        conflict_path = current_file.with_suffix(current_file.suffix + ".conflict")
                        conflict_path.write_bytes(new_bytes)
                    return "conflict"
                elif new_bytes != base_bytes:
                    if not dry_run:
                        current_file.write_bytes(new_bytes)
                    return "clean"
                return "clean"

            base_content = base_file.read_text(encoding="utf-8") if base_file.exists() else ""
            current_content = current_file.read_text(encoding="utf-8")
            new_content = new_file.read_text(encoding="utf-8")

            # Check which sides changed
            user_changed = current_content != base_content
            template_changed = new_content != base_content

            if not user_changed and not template_changed:
                return "clean"
            elif user_changed and not template_changed:
                return "clean"
            elif not user_changed and template_changed:
                if not dry_run:
                    current_file.write_text(new_content, encoding="utf-8")
                return "clean"
            else:
                # Both changed — 3-way merge
                merged, has_conflicts = git_utils.merge_file(base_content, current_content, new_content)
                if not dry_run:
                    current_file.write_text(merged, encoding="utf-8")
                return "conflict" if has_conflicts else "clean"

        except Exception as exc:
            return f"Failed to merge {relative_path}: {exc}"

    def _is_binary(self, path: Path) -> bool:
        """Heuristic check for binary files."""
        try:
            chunk = path.read_bytes()[:8192]
            return b"\x00" in chunk
        except Exception:  # nosec B110
            return False
