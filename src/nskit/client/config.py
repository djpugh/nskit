"""Recipe configuration persistence."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from nskit.client.exceptions import InvalidConfigError, ProjectNotRecipeBasedError


class RecipeMetadata(BaseModel):
    """Metadata about the recipe used to generate the project.

    Args:
        recipe_name: Name of the recipe.
        docker_image: Docker image URL used for generation.
        github_repo: Optional GitHub repository URL.
        created_at: Timestamp when the project was created.
        updated_at: Timestamp of the last update.
    """

    recipe_name: str
    docker_image: str
    github_repo: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecipeConfig(BaseModel):
    """Recipe configuration persisted in a project.

    Args:
        input: Original input parameters used for generation.
        rendered: Rendered/resolved parameter values.
        metadata: Recipe metadata (name, image, timestamps).
    """

    input: dict[str, Any] = Field(default_factory=dict)
    rendered: dict[str, Any] = Field(default_factory=dict)
    metadata: RecipeMetadata | None = None


class ConfigManager:
    """Manages recipe configuration files.

    Args:
        project_path: Root path of the project.
        config_dir: Directory name for config storage (default ``.recipe``).
        config_filename: Config file name (default ``config.yml``).
    """

    def __init__(
        self,
        project_path: Path,
        config_dir: str = ".recipe",
        config_filename: str = "config.yml",
    ) -> None:
        self.project_path = project_path
        self.config_dir = config_dir
        self.config_filename = config_filename
        self.config_path = project_path / config_dir / config_filename

    def load_config(self) -> RecipeConfig:
        """Load recipe configuration from YAML.

        Returns:
            Parsed ``RecipeConfig`` instance.

        Raises:
            ProjectNotRecipeBasedError: If the config file does not exist.
            InvalidConfigError: If the YAML is invalid or cannot be parsed.
        """
        if not self.config_path.exists():
            raise ProjectNotRecipeBasedError(str(self.project_path))

        raw = self.config_path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise InvalidConfigError([str(exc)]) from exc

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise InvalidConfigError([f"Expected a mapping, got {type(data).__name__}"])

        try:
            return RecipeConfig.model_validate(data)
        except Exception as exc:
            raise InvalidConfigError([str(exc)]) from exc

    def save_config(self, config: RecipeConfig) -> None:
        """Save recipe configuration to YAML.

        Creates the config directory if it does not exist. Serialises
        datetime fields to ISO format strings.

        Args:
            config: Configuration to persist.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json")
        content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        self.config_path.write_text(content, encoding="utf-8")

    def update_config_version(self, new_version: str, recipe_name: str) -> None:
        """Update the Docker image version and timestamp in the config.

        Args:
            new_version: New version tag to set.
            recipe_name: Recipe name (used if metadata is missing).
        """
        config = self.load_config()
        if config.metadata is None:
            config.metadata = RecipeMetadata(
                recipe_name=recipe_name,
                docker_image=f"{recipe_name}:{new_version}",
            )
        else:
            # Replace version tag in docker_image URL
            current_image = config.metadata.docker_image
            config.metadata.docker_image = re.sub(r":[^/]+$", f":{new_version}", current_image)
        config.metadata.updated_at = datetime.now(tz=timezone.utc)
        self.save_config(config)

    def is_recipe_based(self) -> bool:
        """Check whether the project has a recipe configuration file.

        Returns:
            ``True`` if the config file exists, ``False`` otherwise.
        """
        return self.config_path.exists()
