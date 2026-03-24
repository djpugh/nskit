"""Recipes module initialization (moved to nskit.client)."""
# Backward compatibility - re-export from new location
from nskit.client import RecipeClient, UpdateClient, DiscoveryClient
from nskit.client.engines import DockerEngine, LocalEngine
from nskit.client.models import RecipeInfo, RecipeResult, UpdateResult, RepositoryInfo
from nskit.recipes.repository_client import RepositoryClient

# Backward compatibility for ExecutionMode (deprecated)
from nskit.client.execution import ExecutionMode

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
