"""Docker backend for recipe management."""
import subprocess
from pathlib import Path
from typing import List, Optional

from nskit.client.backends.base import RecipeBackend
from nskit.client.models import RecipeInfo


class DockerBackend(RecipeBackend):
    """Backend that fetches recipes from Docker registry."""

    def __init__(
        self,
        registry_url: str = "ghcr.io",
        image_prefix: str = "",
        auth_token: Optional[str] = None,
        entrypoint: str = "nskit.recipes",
    ):
        """Initialize Docker backend.
        
        Args:
            registry_url: Docker registry URL (e.g., ghcr.io)
            image_prefix: Prefix for image names (e.g., org/project)
            auth_token: Optional authentication token
            entrypoint: Recipe entrypoint name
        """
        self.registry_url = registry_url
        self.image_prefix = image_prefix
        self.auth_token = auth_token
        self._entrypoint = entrypoint
        self._check_docker()

    def _check_docker(self) -> None:
        """Check if Docker is installed and running."""
        try:
            subprocess.run(
                ["docker", "info"],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Docker is not running. Please start Docker Desktop or the Docker daemon."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Docker is not responding. Please check if Docker is running properly."
            )

    @property
    def entrypoint(self) -> str:
        """Get the recipe entrypoint."""
        return self._entrypoint

    def _build_image_url(self, recipe_name: str, version: str) -> str:
        """Build Docker image URL."""
        if self.image_prefix:
            return f"{self.registry_url}/{self.image_prefix}/{recipe_name}:{version}"
        return f"{self.registry_url}/{recipe_name}:{version}"

    def _authenticate(self) -> None:
        """Authenticate with Docker registry if token provided."""
        if not self.auth_token:
            return

        subprocess.run(
            ["docker", "login", self.registry_url, "-u", "token", "--password-stdin"],
            input=self.auth_token,
            text=True,
            check=True,
            capture_output=True,
        )

    def list_recipes(self) -> List[RecipeInfo]:
        """List available recipes.
        
        Note: Docker registries don't provide easy listing.
        This is a limitation of the Docker backend.
        """
        return []

    def get_recipe_versions(self, recipe_name: str) -> List[str]:
        """Get available versions for a recipe.
        
        Note: Requires external API or manifest inspection.
        Returns empty list as Docker doesn't provide easy version listing.
        """
        return []

    def fetch_recipe(
        self, recipe_name: str, version: str, target_path: Path
    ) -> Path:
        """Fetch recipe from Docker image.
        
        Args:
            recipe_name: Recipe name
            version: Recipe version
            target_path: Where to extract recipe
            
        Returns:
            Path to extracted recipe
        """
        self._authenticate()

        image_url = self._build_image_url(recipe_name, version)

        # Pull image
        subprocess.run(
            ["docker", "pull", image_url],
            check=True,
            capture_output=True,
        )

        # Extract recipe files from image
        # Create temporary container to copy files
        result = subprocess.run(
            ["docker", "create", image_url],
            check=True,
            capture_output=True,
            text=True,
        )
        container_id = result.stdout.strip()

        try:
            # Copy recipe files from container
            subprocess.run(
                ["docker", "cp", f"{container_id}:/app/recipes/", str(target_path)],
                check=True,
            )
        finally:
            # Remove temporary container
            subprocess.run(
                ["docker", "rm", container_id],
                check=True,
                capture_output=True,
            )

        return target_path / recipe_name

    def get_image_url(self, recipe: str, version: str) -> str:
        """Get Docker image URL for a recipe."""
        return self._build_image_url(recipe, version)

    def pull_image(self, image_url: str) -> None:
        """Pull Docker image."""
        self._authenticate()
        subprocess.run(
            ["docker", "pull", image_url],
            check=True,
            capture_output=True,
        )
