"""GitHub backend for recipe management."""

from __future__ import annotations

import subprocess  # nosec B404
import tempfile
import zipfile
from pathlib import Path

from pydantic import SecretStr

try:
    from ghapi.core import GhApi
except ImportError:
    GhApi = None

from nskit._logging import logger_factory
from nskit.client.backends.base import RecipeBackend
from nskit.client.models import RecipeInfo
from nskit.client.validation import validate_image_url, validate_recipe_name, validate_version
from nskit.constants import RECIPE_ENTRYPOINT

logger = logger_factory.get_logger(__name__)


class GitHubBackend(RecipeBackend):
    """Backend that fetches recipes from GitHub releases."""

    def __init__(
        self,
        org: str,
        repo_pattern: str = "{recipe_name}",
        token: str | SecretStr | None = None,
        entrypoint: str = RECIPE_ENTRYPOINT,
    ):
        """Initialize GitHub backend.

        Args:
            org: GitHub organization.
            repo_pattern: Pattern for repository names (use {recipe_name} placeholder).
            token: Optional GitHub token (str or SecretStr; uses gh CLI if not provided).
            entrypoint: Recipe entrypoint name.
        """
        self.org = org
        self.repo_pattern = repo_pattern
        self._token: SecretStr | None = SecretStr(token) if isinstance(token, str) else token
        self._github: GhApi | None = None
        self._entrypoint = entrypoint
        if GhApi is None:
            raise ImportError("GitHubBackend requires ghapi. Install with: pip install nskit[github]")

    @property
    def entrypoint(self) -> str:
        """Get the recipe entrypoint."""
        return self._entrypoint

    def _get_token(self) -> str:
        """Get GitHub token from gh CLI or provided token.

        Returns:
            GitHub token string.

        Raises:
            RuntimeError: If gh CLI is not found or not authenticated.
        """
        if self._token:
            return self._token.get_secret_value()
        try:
            result = subprocess.run(  # nosec B603, B607
                ["gh", "auth", "token"], check=True, capture_output=True, text=True
            )
            self._token = SecretStr(result.stdout.strip())
            return self._token.get_secret_value()
        except FileNotFoundError:
            raise RuntimeError("GitHub CLI (gh) not found. Please install it: https://cli.github.com/") from None
        except subprocess.CalledProcessError:
            raise RuntimeError("GitHub authentication required. Please run: gh auth login") from None

    def _get_client(self) -> GhApi:
        """Get authenticated GitHub client.

        Returns:
            Authenticated ``GhApi`` instance.
        """
        if self._github is None:
            self._github = GhApi(token=self._get_token())
        return self._github

    def _get_repo_name(self, recipe_name: str) -> str:
        """Build repository name from pattern.

        Args:
            recipe_name: Recipe name.

        Returns:
            Repository name string.
        """
        validate_recipe_name(recipe_name)
        return self.repo_pattern.format(recipe_name=recipe_name)

    def list_recipes(self) -> list[RecipeInfo]:
        """List available recipes from GitHub org.

        Returns:
            List of recipe information from the organization's repositories.
        """
        from nskit.client.backends.image_labels import get_recipe_name, read_remote_labels

        github = self._get_client()
        repos = github.repos.list_for_org(self.org, type="public")

        recipes = []
        for repo in repos:
            try:
                releases = github.repos.list_releases(self.org, repo.name)
                versions = [r.tag_name for r in releases if not r.draft]
            except Exception:
                logger.warning("Could not fetch releases for %s/%s — skipping", self.org, repo.name)
                versions = []

            name = repo.name
            if versions:
                image_url = self.get_image_url(name, versions[0])
                try:
                    labels = read_remote_labels(image_url, token=self._get_token())
                    name = get_recipe_name(labels) or name
                except Exception:
                    logger.debug("Failed to read labels for %s", image_url, exc_info=True)

            recipes.append(RecipeInfo(name=name, versions=versions, description=repo.description))
        return recipes

    def get_recipe_versions(self, recipe_name: str) -> list[str]:
        """Get available versions for a recipe.

        Args:
            recipe_name: Recipe name.

        Returns:
            List of version tag strings.
        """
        github = self._get_client()
        repo_name = self._get_repo_name(recipe_name)
        try:
            releases = github.repos.list_releases(self.org, repo_name)
            return [r.tag_name for r in releases if not r.draft]
        except Exception:
            logger.warning("Could not fetch versions for recipe '%s'", recipe_name)
            return []

    def fetch_recipe(self, recipe_name: str, version: str, target_path: Path) -> Path:
        """Fetch recipe from GitHub release.

        Args:
            recipe_name: Recipe name.
            version: Recipe version (tag name).
            target_path: Where to extract recipe.

        Returns:
            Path to extracted recipe.
        """
        github = self._get_client()
        repo_name = self._get_repo_name(recipe_name)
        github.repos.get_release_by_tag(self.org, repo_name, version)

        archive_url = f"https://github.com/{self.org}/{repo_name}/archive/refs/tags/{version}.zip"

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            subprocess.run(  # nosec B603, B607
                ["curl", "-L", "-o", tmp.name, archive_url], check=True, capture_output=True
            )
            # Extract archive (with zip-slip protection)
            with zipfile.ZipFile(tmp.name, "r") as zip_ref:
                for member in zip_ref.namelist():
                    member_path = (target_path / member).resolve()
                    if not str(member_path).startswith(str(target_path.resolve())):
                        raise ValueError(f"Zip entry {member!r} would escape target directory")
                zip_ref.extractall(target_path)

        # GitHub archives extract to {repo}-{tag}/ directory
        extracted_dir = target_path / f"{repo_name}-{version.lstrip('v')}"
        if not extracted_dir.exists():
            extracted_dir = target_path / f"{repo_name}-{version}"
        return extracted_dir

    def get_image_url(self, recipe: str, version: str) -> str:
        """Get Docker image URL from GitHub Container Registry.

        Args:
            recipe: Recipe name.
            version: Recipe version.

        Returns:
            Docker image URL.
        """
        repo_name = self._get_repo_name(recipe)
        validate_version(version)
        return f"ghcr.io/{self.org}/{repo_name}:{version}"

    def pull_image(self, image_url: str) -> None:
        """Pull Docker image from GitHub Container Registry.

        Args:
            image_url: Docker image URL to pull.
        """
        validate_image_url(image_url)
        token = self._get_token()
        subprocess.run(  # nosec B603, B607
            ["docker", "login", "ghcr.io", "-u", "token", "--password-stdin"],
            input=token,
            text=True,
            check=True,
            capture_output=True,
        )
        subprocess.run(["docker", "pull", image_url], check=True, capture_output=True)  # nosec B603, B607
