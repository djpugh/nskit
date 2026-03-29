"""Backend configuration and factory.

Built-in backends are registered in ``_BUILTIN_REGISTRY``.  Third-party
backends are discovered automatically via the ``nskit.backends``
entry-point group.  Each entry point should resolve to a
``(ConfigModel, BackendClass)`` tuple.

Example third-party ``pyproject.toml``::

    [project.entry-points."nskit.backends"]
    s3 = "my_package.backends:S3BackendConfig, S3Backend"
"""

from __future__ import annotations

from pathlib import Path

import yaml

from nskit._logging import logger_factory
from nskit.client.backends.base import RecipeBackend
from nskit.client.backends.docker import DockerBackend
from nskit.client.backends.github import GitHubBackend
from nskit.client.backends.local import LocalBackend
from nskit.client.backends.settings import DockerBackendConfig, GitHubBackendConfig, LocalBackendConfig
from nskit.common.extensions import get_extensions
from nskit.constants import BACKENDS_ENTRYPOINT

logger = logger_factory.get_logger(__name__)

# Built-in backends — always available.
_BUILTIN_REGISTRY: dict[str, tuple[type, type[RecipeBackend]]] = {
    "local": (LocalBackendConfig, LocalBackend),
    "docker": (DockerBackendConfig, DockerBackend),
    "github": (GitHubBackendConfig, GitHubBackend),
}


def _build_registry() -> dict[str, tuple[type, type[RecipeBackend]]]:
    """Merge built-in backends with any discovered via entry points."""
    registry = dict(_BUILTIN_REGISTRY)
    for name, ep in get_extensions(BACKENDS_ENTRYPOINT).items():
        try:
            config_cls, backend_cls = ep.load()
            registry[name] = (config_cls, backend_cls)
        except Exception:
            logger.warning("Failed to load backend entry point %r", name, exc_info=True)
    return registry


def create_backend_from_config(config: dict | Path | str) -> RecipeBackend:
    """Create a backend from a config dict or YAML file.

    Looks up the ``type`` key in the registry (built-in + entry-point
    discovered), validates the remaining keys through the corresponding
    pydantic model, and constructs the backend.

    Args:
        config: Dict, or path to a YAML config file.

    Returns:
        Configured backend instance.
    """
    if isinstance(config, (Path, str)):
        with open(config) as f:
            config = yaml.safe_load(f)

    backend_type = config.get("type", "local")
    registry = _build_registry()

    entry = registry.get(backend_type)
    if entry is None:
        raise ValueError(f"Unknown backend type: {backend_type!r}. Available: {', '.join(sorted(registry))}")

    config_cls, backend_cls = entry
    validated = config_cls(**config)
    return backend_cls(**validated.model_dump(exclude={"type"}))
