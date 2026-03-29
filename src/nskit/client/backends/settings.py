"""Backend and engine configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, Field, SecretStr

from nskit.constants import RECIPE_ENTRYPOINT


class DockerTimeouts(BaseModel):
    """Timeout configuration for Docker operations (seconds)."""

    pull: int = 600
    cmd: int = 30
    file_copy: int = 120


class EngineTimeouts(BaseModel):
    """Timeout configuration for Docker engine operations (seconds)."""

    pull: int = 600
    run: int = 600


class LocalBackendConfig(BaseModel):
    """Configuration for the local filesystem backend."""

    type: Literal["local"] = "local"
    recipes_dir: Path
    entrypoint: str = RECIPE_ENTRYPOINT


class DockerBackendConfig(BaseModel):
    """Configuration for the Docker registry backend."""

    type: Literal["docker"] = "docker"
    registry_url: str = "ghcr.io"
    image_prefix: str = ""
    auth_token: SecretStr | None = None
    entrypoint: str = RECIPE_ENTRYPOINT
    timeouts: DockerTimeouts = Field(default_factory=DockerTimeouts)


class GitHubBackendConfig(BaseModel):
    """Configuration for the GitHub releases backend."""

    type: Literal["github"] = "github"
    org: str
    repo_pattern: str = "{recipe_name}"
    token: SecretStr | None = None
    entrypoint: str = RECIPE_ENTRYPOINT


BackendConfig = Union[LocalBackendConfig, DockerBackendConfig, GitHubBackendConfig]
