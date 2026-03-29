"""Execution modes for recipe initialization."""

from enum import Enum


class ExecutionMode(str, Enum):
    """Recipe execution mode."""

    DOCKER = "docker"  # Run recipe in Docker container (default, production)
    LOCAL = "local"  # Run recipe from locally installed package (development)
