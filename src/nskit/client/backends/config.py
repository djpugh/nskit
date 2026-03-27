"""Backend configuration and factory."""

from pathlib import Path
from typing import Union

import yaml

from nskit.client.backends.base import RecipeBackend
from nskit.client.backends.docker import DockerBackend
from nskit.client.backends.github import GitHubBackend
from nskit.client.backends.local import LocalBackend

_DEFAULT_ENTRYPOINT = "nskit.recipes"


def create_backend_from_config(config: Union[dict, Path, str]) -> RecipeBackend:
    """Create backend from configuration.

    Args:
        config: Dict config or path to YAML config file

    Returns:
        Configured backend instance

    Example config:
        type: local
        path: /path/to/recipes

        type: docker
        registry_url: ghcr.io
        image_prefix: org/project
        auth_token: ${GITHUB_TOKEN}

        type: github
        org: myorg
        repo_pattern: recipe-{recipe_name}
        token: ${GITHUB_TOKEN}
    """
    if isinstance(config, (Path, str)):
        with open(config) as f:
            config = yaml.safe_load(f)

    backend_type = config.get("type", "local")

    if backend_type == "local":
        return LocalBackend(
            recipes_dir=Path(config["path"]),
            entrypoint=config.get("entrypoint", _DEFAULT_ENTRYPOINT),
        )

    elif backend_type == "docker":
        return DockerBackend(
            registry_url=config.get("registry_url", "ghcr.io"),
            image_prefix=config.get("image_prefix", ""),
            auth_token=config.get("auth_token"),
            entrypoint=config.get("entrypoint", _DEFAULT_ENTRYPOINT),
        )

    elif backend_type == "github":
        return GitHubBackend(
            org=config["org"],
            repo_pattern=config.get("repo_pattern", "{recipe_name}"),
            token=config.get("token"),
            entrypoint=config.get("entrypoint", _DEFAULT_ENTRYPOINT),
        )

    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
