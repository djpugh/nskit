"""Docker backend for recipe management."""

import subprocess  # nosec B404
from pathlib import Path
from typing import Optional

from pydantic import SecretStr

from nskit._logging import logger_factory
from nskit.client.backends.base import RecipeBackend
from nskit.client.backends.settings import DockerTimeouts
from nskit.client.models import RecipeInfo
from nskit.client.validation import validate_image_url, validate_recipe_name, validate_version

logger = logger_factory.get_logger(__name__)


class DockerBackend(RecipeBackend):
    """Backend that fetches recipes from Docker registry."""

    def __init__(
        self,
        registry_url: str = "ghcr.io",
        image_prefix: str = "",
        auth_token: Optional[str | SecretStr] = None,
        entrypoint: str = "nskit.recipes",
        timeouts: DockerTimeouts | None = None,
    ):
        """Initialize Docker backend.

        Args:
            registry_url: Docker registry URL (e.g., ghcr.io).
            image_prefix: Prefix for image names (e.g., org/project).
            auth_token: Optional authentication token (str or SecretStr).
            entrypoint: Recipe entrypoint name.
            timeouts: Timeout configuration for Docker operations.
        """
        self.registry_url = registry_url
        self.image_prefix = image_prefix
        self._auth_token = SecretStr(auth_token) if isinstance(auth_token, str) else auth_token
        self._entrypoint = entrypoint
        self.timeouts = timeouts or DockerTimeouts()
        self._check_docker()

    @property
    def entrypoint(self) -> str:
        """Get the recipe entrypoint."""
        return self._entrypoint

    def _check_docker(self) -> None:
        """Check if Docker is installed and running."""
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=5)  # nosec B603, B607
        except FileNotFoundError:
            raise RuntimeError("Docker not found. Please install Docker: https://docs.docker.com/get-docker/") from None
        except subprocess.CalledProcessError:
            raise RuntimeError("Docker is not running. Please start Docker Desktop or the Docker daemon.") from None
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker is not responding. Please check if Docker is running properly.") from None

    def _build_image_url(self, recipe_name: str, version: str) -> str:
        """Build Docker image URL.

        Args:
            recipe_name: Recipe name.
            version: Recipe version.

        Returns:
            Full image URL string.
        """
        validate_recipe_name(recipe_name)
        validate_version(version)
        if self.image_prefix:
            return f"{self.registry_url}/{self.image_prefix}/{recipe_name}:{version}"
        return f"{self.registry_url}/{recipe_name}:{version}"

    def _authenticate(self) -> None:
        """Authenticate with Docker registry if token provided."""
        if not self._auth_token:
            return
        subprocess.run(  # nosec B603, B607
            ["docker", "login", self.registry_url, "-u", "token", "--password-stdin"],
            input=self._auth_token.get_secret_value(),
            text=True,
            check=True,
            capture_output=True,
        )

    def list_recipes(self) -> list[RecipeInfo]:
        """List available recipes.

        Note: Docker registries don't provide easy listing.
        This is a limitation of the Docker backend.
        """
        return []

    def get_recipe_versions(self, recipe_name: str) -> list[str]:
        """Get available versions for a recipe.

        Note: Requires external API or manifest inspection.
        Returns empty list as Docker doesn't provide easy version listing.
        """
        return []

    def fetch_recipe(self, recipe_name: str, version: str, target_path: Path) -> Path:
        """Fetch recipe from Docker image.

        Args:
            recipe_name: Recipe name.
            version: Recipe version.
            target_path: Where to extract recipe.

        Returns:
            Path to extracted recipe.
        """
        self._authenticate()
        image_url = self._build_image_url(recipe_name, version)

        subprocess.run(["docker", "pull", image_url], check=True, capture_output=True, timeout=self.timeouts.pull)  # nosec B603, B607

        result = subprocess.run(  # nosec B603, B607
            ["docker", "create", image_url], check=True, capture_output=True, text=True, timeout=self.timeouts.cmd
        )
        container_id = result.stdout.strip()

        try:
            subprocess.run(  # nosec B603, B607
                ["docker", "cp", f"{container_id}:/app/recipes/", str(target_path)],
                check=True,
                timeout=self.timeouts.file_copy,
            )
        finally:
            subprocess.run(  # nosec B603, B607
                ["docker", "rm", container_id], check=True, capture_output=True, timeout=self.timeouts.cmd
            )

        return target_path / recipe_name

    def get_image_url(self, recipe: str, version: str) -> str:
        """Get Docker image URL for a recipe.

        Args:
            recipe: Recipe name.
            version: Recipe version.

        Returns:
            Docker image URL.
        """
        return self._build_image_url(recipe, version)

    def pull_image(self, image_url: str) -> None:
        """Pull Docker image.

        Args:
            image_url: Docker image URL to pull.
        """
        validate_image_url(image_url)
        self._authenticate()
        subprocess.run(  # nosec B603, B607
            ["docker", "pull", image_url], check=True, capture_output=True, timeout=self.timeouts.pull
        )
