"""Recipes module initialization (moved to nskit.client)."""
# Backward compatibility - re-export from new location
from nskit.client import DiscoveryClient, RecipeClient, UpdateClient
from nskit.client.engines import DockerEngine, LocalEngine

# Backward compatibility for ExecutionMode (deprecated)
from nskit.client.execution import ExecutionMode
from nskit.client.models import RecipeInfo, RecipeResult, RepositoryInfo, UpdateResult
from nskit.recipes.repository_client import RepositoryClient

__all__ = [
    "RecipeClient",
    "DiscoveryClient",
    "RecipeInfo",
    "RecipeResult",
    "RepositoryClient",
    "RepositoryInfo",
    "UpdateClient",
    "UpdateResult",
    "ExecutionMode",  # Deprecated
    "DockerEngine",
    "LocalEngine",
]
