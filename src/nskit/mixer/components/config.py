"""Generic configuration classes for recipes."""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ConfigNotFoundError(Exception):
    """Raised when a configuration file is not found."""

    pass


class InvalidConfigError(Exception):
    """Raised when a configuration file is invalid."""

    pass


class FileSystemError(Exception):
    """Raised when there's a filesystem error during config operations."""

    pass


class RecipeMetadata(BaseModel):
    """Metadata for a recipe configuration."""

    recipe_name: str = Field(..., description="Name of the recipe template")
    recipe_version: Optional[str] = Field(None, description="Version of the recipe")
    docker_image: Optional[str] = Field(None, description="Docker image used for generation")
    created_at: Optional[datetime] = Field(None, description="When the project was created")
    updated_at: Optional[datetime] = Field(None, description="When the project was last updated")


class RecipeConfig(BaseModel):
    """Configuration structure for recipes."""

    metadata: Optional[RecipeMetadata] = Field(None, description="Recipe metadata")
    input: dict[str, Any] = Field(default_factory=dict, description="Input fields for the recipe")
    rendered: dict[str, Any] = Field(default_factory=dict, description="Computed/derived fields")

    @classmethod
    def load_from_file(cls, file_path: Path) -> "RecipeConfig":
        """Load configuration from a YAML file."""
        try:
            if not file_path.exists():
                raise ConfigNotFoundError(f"Configuration file not found: {file_path}")

            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise InvalidConfigError(f"Configuration file must contain a YAML dictionary: {file_path}")

            return cls(**data)

        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Invalid YAML in configuration file {file_path}: {e}") from None
        except OSError as e:
            raise FileSystemError(f"Error reading configuration file {file_path}: {e}") from None

    def save_to_file(self, file_path: Path) -> None:
        """Save configuration to a YAML file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.model_dump(mode="json")

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, indent=2)

        except OSError as e:
            raise FileSystemError(f"Error writing configuration file {file_path}: {e}") from None
