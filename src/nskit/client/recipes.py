"""Recipe client for programmatic recipe operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nskit.client.backends.base import RecipeBackend
from nskit.client.engines import DockerEngine, RecipeEngine
from nskit.client.models import RecipeInfo, RecipeResult


def _read_recipe_label(image_url: str) -> str | None:
    """Read nskit.recipe.name label from a pulled Docker image."""
    from nskit.client.backends.image_labels import get_recipe_name, read_local_labels

    return get_recipe_name(read_local_labels(image_url))


def _detect_repo_client():
    """Try to auto-detect a VCS provider. Returns (client, provider_name) or (None, None)."""
    try:
        from nskit.vcs.provider_detection import get_default_repo_client

        client = get_default_repo_client()
        provider_name = type(client).__name__.replace("RepoClient", "")
        return client, provider_name
    except (ValueError, ImportError):
        return None, None


class RecipeClient:
    """Pure Python client for recipe operations (no CLI dependencies)."""

    def __init__(self, backend: RecipeBackend, engine: RecipeEngine | None = None):
        """Initialize the recipe client.

        Args:
            backend: Backend for recipe discovery and fetching
            engine: Execution engine (defaults to DockerEngine)
        """
        self.backend = backend
        if engine is None:
            from nskit.client.backends.docker_local import DockerLocalBackend

            engine = DockerEngine(skip_pull=isinstance(backend, DockerLocalBackend))
        self.engine = engine

    def list_recipes(self) -> list[RecipeInfo]:
        """List all available recipes from the backend.

        Returns:
            List of recipe information
        """
        return self.backend.list_recipes()

    def get_recipe_versions(self, recipe: str) -> list[str]:
        """Get available versions for a specific recipe.

        Args:
            recipe: Recipe name

        Returns:
            List of available versions
        """
        return self.backend.get_recipe_versions(recipe)

    def initialize_recipe(
        self,
        recipe: str,
        version: str,
        parameters: dict[str, Any],
        output_dir: Path,
        force: bool = False,
    ) -> RecipeResult:
        """Initialize a new project from a recipe.

        Args:
            recipe: Recipe name
            version: Recipe version
            parameters: Recipe parameters
            output_dir: Output directory for the project
            force: Allow initialization in non-empty directory

        Returns:
            Result of the initialization
        """
        errors = []

        # Check output directory
        if output_dir.exists() and any(output_dir.iterdir()) and not force:
            errors.append(f"Output directory {output_dir} is not empty. Use force=True to override.")
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
            )

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Get image URL from backend (only if backend supports it and engine needs it)
            image_url = None
            if hasattr(self.engine, "__class__") and self.engine.__class__.__name__ == "DockerEngine":
                if hasattr(self.backend, "get_image_url"):
                    image_url = self.backend.get_image_url(recipe, version)
                    if hasattr(self.backend, "pull_image"):
                        self.backend.pull_image(image_url)
                    # Read canonical recipe name from image label
                    recipe = _read_recipe_label(image_url) or recipe

            # Execute using engine
            return self.engine.execute(
                recipe=recipe,
                version=version,
                parameters=parameters,
                output_dir=output_dir,
                image_url=image_url,
                entrypoint=self.backend.entrypoint,
            )

        except Exception as e:
            errors.append(str(e))
            return RecipeResult(
                success=False,
                project_path=output_dir,
                recipe_name=recipe,
                recipe_version=version,
                errors=errors,
            )

    def create_repository(
        self,
        repo_name: str,
        project_path: Path | None = None,
        description: str | None = None,
        private: bool = True,
    ) -> tuple[bool, str]:
        """Create a remote repository and optionally push the project.

        Auto-detects the VCS provider from environment variables.
        If *project_path* is provided and contains a git repo, the
        project is committed and pushed to the new remote.

        Args:
            repo_name: Repository name.
            project_path: Local project directory to push.
            description: Repository description.
            private: Whether the repository should be private.

        Returns:
            Tuple of (success, message).
        """
        from nskit.recipes.repository_client import RepositoryClient

        client, provider = _detect_repo_client()
        if client is None:
            return False, "No VCS provider detected. Set appropriate environment variables (e.g. GITHUB_TOKEN)."

        try:
            repo_client = RepositoryClient(vcs_client=client)
            if project_path and (project_path / ".git").is_dir():
                info = repo_client.create_and_push(
                    repo_name,
                    project_path,
                    description=description,
                    private=private,
                )
                return True, f"Created and pushed to {info.url}"
            else:
                info = repo_client.create_repository(repo_name, description=description, private=private)
                return True, f"Created repository at {info.url}"
        except Exception as e:
            return False, f"Failed to create repository: {e}"
