"""Environment variable resolver with prefix-based security."""
from __future__ import annotations

import os
from typing import ClassVar


class EnvVarResolver:
    """Resolves field defaults from environment variables with prefix security.

    Only environment variables whose names match at least one allowed prefix
    are resolved. This prevents recipes from reading arbitrary environment
    variables.

    Args:
        allowed_prefixes: List of allowed prefixes. Defaults to
            ``["NSKIT_", "RECIPE_"]``.
    """

    DEFAULT_PREFIXES: ClassVar[list[str]] = ["NSKIT_", "RECIPE_"]

    def __init__(self, allowed_prefixes: list[str] | None = None) -> None:
        self.allowed_prefixes = allowed_prefixes or self.DEFAULT_PREFIXES

    def resolve(self, env_var_name: str) -> str | None:
        """Resolve an environment variable if it matches an allowed prefix.

        Args:
            env_var_name: Name of the environment variable to resolve.

        Returns:
            The environment variable value if the name matches an allowed
            prefix and the variable is set, otherwise ``None``.
        """
        if not self._is_allowed(env_var_name):
            return None
        return os.environ.get(env_var_name)

    def _is_allowed(self, env_var_name: str) -> bool:
        """Check whether the variable name starts with any allowed prefix."""
        return any(env_var_name.startswith(prefix) for prefix in self.allowed_prefixes)
