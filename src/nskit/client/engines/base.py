"""Execution engine interface."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from nskit.client.models import RecipeResult


class RecipeEngine(ABC):
    """Abstract interface for recipe execution engines."""

    @abstractmethod
    def execute(
        self,
        recipe: str,
        version: str,
        parameters: Dict[str, Any],
        output_dir: Path,
        image_url: str = None,
        entrypoint: str = None,
    ) -> RecipeResult:
        """Execute a recipe.
        
        Args:
            recipe: Recipe name
            version: Recipe version
            parameters: Recipe parameters
            output_dir: Output directory
            image_url: Docker image URL (for Docker engine)
            entrypoint: Recipe entrypoint (for Local engine)
            
        Returns:
            Recipe execution result
        """
        pass
