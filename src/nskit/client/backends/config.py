"""Backend configuration and factory.

The factory uses a registry that maps backend ``type`` strings (from YAML
config) to a ``(ConfigModel, BackendClass)`` pair.  The config dict is
validated through the pydantic model, then the backend is constructed via
its ``from_config`` classmethod.

Third-party backends can be registered with ``register_backend``.
"""

from pathlib import Path
from typing import Union

import yaml

from nskit.client.backends.base import RecipeBackend
from nskit.client.backends.docker import DockerBackend
from nskit.client.backends.github import GitHubBackend
from nskit.client.backends.local import LocalBackend
from nskit.client.backends.settings import DockerBackendConfig, GitHubBackendConfig, LocalBackendConfig

# Maps type string → (pydantic config model, backend class)
_REGISTRY: dict[str, tuple[type, type[RecipeBackend]]] = {
    "local": (LocalBackendConfig, LocalBackend),
    "docker": (DockerBackendConfig, DockerBackend),
    "github": (GitHubBackendConfig, GitHubBackend),
}


def register_backend(type_name: str, config_cls: type, backend_cls: type[RecipeBackend]) -> None:
    """Register a custom backend type.

    Args:
        type_name: The ``type`` value used in YAML config files.
        config_cls: Pydantic model that validates the config dict.
        backend_cls: Backend class with a ``from_config(cls, config)``
            classmethod.
    """
    _REGISTRY[type_name] = (config_cls, backend_cls)


def create_backend_from_config(config: Union[dict, Path, str]) -> RecipeBackend:
    """Create a backend from a config dict or YAML file.

    Looks up the ``type`` key in the registry, validates the remaining
    keys through the corresponding pydantic model, and constructs the
    backend via ``Backend.from_config(validated_config)``.

    Args:
        config: Dict, or path to a YAML config file.

    Returns:
        Configured backend instance.
    """
    if isinstance(config, (Path, str)):
        with open(config) as f:
            config = yaml.safe_load(f)

    backend_type = config.get("type", "local")

    entry = _REGISTRY.get(backend_type)
    if entry is None:
        raise ValueError(f"Unknown backend type: {backend_type!r}. Available: {', '.join(sorted(_REGISTRY))}")

    config_cls, backend_cls = entry
    validated = config_cls(**config)
    return backend_cls.from_config(validated)
