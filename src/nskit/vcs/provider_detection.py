"""VCS provider auto-detection."""
from __future__ import annotations

from pydantic import ValidationError

from nskit._logging import logger_factory
from nskit.vcs.providers import ProviderEnum
from nskit.vcs.providers.abstract import RepoClient

logger = logger_factory.get_logger(__name__)


def get_default_repo_client() -> RepoClient:
    """Auto-detect and return a configured VCS provider's repo client.

    Iterates through registered providers (via the ``nskit.vcs.providers``
    entry point) and returns the client for the last one that initialises
    successfully from environment variables.

    Raises:
        ValueError: If no provider could be configured.
    """
    client = None
    for provider in ProviderEnum:
        try:
            if provider.extension:
                settings = provider.extension()
                client = settings.repo_client
                logger.info(f"{provider.value} configured.")
            else:
                raise ValueError("Extension not found")
        except (ImportError, ValueError, ValidationError):
            logger.info(f"{provider.value} not configured.")
    if client is None:
        raise ValueError(
            "No VCS provider configured. Set appropriate environment variables " "(e.g. GITHUB_TOKEN for GitHub)."
        )
    return client
